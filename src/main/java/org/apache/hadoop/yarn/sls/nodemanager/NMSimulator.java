/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.apache.hadoop.yarn.sls.nodemanager;

import java.io.IOException;
import java.text.MessageFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.DelayQueue;

import org.apache.hadoop.classification.InterfaceAudience.Private;
import org.apache.hadoop.classification.InterfaceStability.Unstable;
import org.apache.hadoop.yarn.api.records.ApplicationId;
import org.apache.hadoop.yarn.api.records.Container;
import org.apache.hadoop.yarn.api.records.ContainerExitStatus;
import org.apache.hadoop.yarn.api.records.ContainerId;
import org.apache.hadoop.yarn.api.records.ContainerState;
import org.apache.hadoop.yarn.api.records.ContainerStatus;
import org.apache.hadoop.yarn.exceptions.YarnException;
import org.apache.hadoop.yarn.server.api.protocolrecords.NodeHeartbeatRequest;
import org.apache.hadoop.yarn.server.api.protocolrecords.NodeHeartbeatResponse;
import org.apache.hadoop.yarn.server.api.protocolrecords
        .RegisterNodeManagerRequest;
import org.apache.hadoop.yarn.server.api.protocolrecords
        .RegisterNodeManagerResponse;
import org.apache.hadoop.yarn.server.api.records.MasterKey;
import org.apache.hadoop.yarn.server.api.records.NodeAction;
import org.apache.hadoop.yarn.server.api.records.NodeHealthStatus;
import org.apache.hadoop.yarn.server.api.records.NodeStatus;
import org.apache.hadoop.yarn.server.resourcemanager.ResourceManager;
import org.apache.hadoop.yarn.server.resourcemanager.rmnode.RMNode;
import org.apache.hadoop.yarn.server.utils.BuilderUtils;
import org.apache.hadoop.yarn.sls.SLSRunner;
import org.apache.hadoop.yarn.sls.conf.SLSConfiguration;
import org.apache.hadoop.yarn.util.Records;
import org.apache.log4j.Logger;

import org.apache.hadoop.yarn.sls.scheduler.ContainerSimulator;
import org.apache.hadoop.yarn.sls.scheduler.TaskRunner;
import org.apache.hadoop.yarn.sls.utils.SLSUtils;
import org.codehaus.jackson.JsonNode;
import org.codehaus.jackson.map.ObjectMapper;
import org.zeromq.ZMQ;

@Private
@Unstable
public class NMSimulator extends TaskRunner.Task {
  // node resource
  private RMNode node;
  // master key
  private MasterKey masterKey;
  // containers with various STATE
  private List<ContainerId> completedContainerList;
  private List<ContainerId> releasedContainerList;
  private DelayQueue<ContainerSimulator> containerQueue;
  /**
   * All containers currently running.
   */
  private Map<ContainerId, ContainerSimulator> runningContainers;

  /**
   * All containers currently waiting for transmissions to complete (transmission phase)
   */
  private List<ContainerSimulator> containersWaitingForTransmission;
  private List<ContainerId> amContainerList;
  // resource manager
  private ResourceManager rm;
  // heart beat response id
  private int RESPONSE_ID = 1;
  private final static Logger LOG = Logger.getLogger(NMSimulator.class);

  private String subscriptionKey;
  private ZMQ.Socket zmqSubscriber;

  public void init(String nodeIdStr, int memory, int cores,
          int dispatchTime, int heartBeatInterval, ResourceManager rm)
          throws IOException, YarnException {
    super.init(dispatchTime, dispatchTime + 1000000L * heartBeatInterval,
            heartBeatInterval);
    // create resource
    String rackHostName[] = SLSUtils.getRackHostName(nodeIdStr);
    this.node = NodeInfo.newNodeInfo(rackHostName[0], rackHostName[1], 
                  BuilderUtils.newResource(memory, cores));
    this.rm = rm;
    // init data structures
    completedContainerList =
            Collections.synchronizedList(new ArrayList<ContainerId>());
    releasedContainerList =
            Collections.synchronizedList(new ArrayList<ContainerId>());
    containerQueue = new DelayQueue<ContainerSimulator>();
    amContainerList =
            Collections.synchronizedList(new ArrayList<ContainerId>());
    runningContainers =
            new ConcurrentHashMap<ContainerId, ContainerSimulator>();
    containersWaitingForTransmission = new ArrayList<ContainerSimulator>();
    // register NM with RM
    RegisterNodeManagerRequest req =
            Records.newRecord(RegisterNodeManagerRequest.class);
    req.setNodeId(node.getNodeID());
    req.setResource(node.getTotalCapability());
    req.setHttpPort(80);
    RegisterNodeManagerResponse response = rm.getResourceTrackerService()
            .registerNodeManager(req);
    masterKey = response.getNMTokenMasterKey();

    // Setup zmq subscriber, subscribe to this node's
    subscriptionKey = this.node.getHostName();
    zmqSubscriber = SLSRunner.getInstance().getZmqContext().socket(ZMQ.SUB);
    zmqSubscriber.connect(SLSRunner.getInstance().getConf().get(SLSConfiguration.NETWORKSIMULATOR_ZMQ_URL));
    zmqSubscriber.subscribe(subscriptionKey.getBytes());
  }

  @Override
  public void firstStep() {
    // do nothing
  }

  @Override
  public void middleStep() throws Exception {
    // Check for completed transmissions
    byte[] msg = zmqSubscriber.recv(ZMQ.DONTWAIT);
    while(msg != null) {
      String message = new String(msg).split("\n")[1];
      msg = zmqSubscriber.recv(ZMQ.DONTWAIT);

      ObjectMapper mapper = new ObjectMapper();
      JsonNode response = mapper.readTree(message);
      if (! response.get("type").getTextValue().equals("TRANSMISSION_SUCCESSFUL")) {
        continue;
      }
      Integer transmissionId = response.get("data").get("transmission_id").getIntValue();

      LOG.info("Transmission complete. transmission_id: " + transmissionId
          + ", duration: " + response.get("data").get("duration").getDoubleValue());

      for (ContainerSimulator cs : containersWaitingForTransmission) {
        cs.notifyTransmissionCompleted(transmissionId);
      }
    }

    // Find all ContainerSimulator done with transmissions phase and start work phase
    List<ContainerSimulator> completed = new ArrayList<ContainerSimulator>();
    for (ContainerSimulator cs : containersWaitingForTransmission) {
      if (cs.isAllTransmissionsCompleted()) {
        cs.startWork();
        completed.add(cs);
      }
    }
    containersWaitingForTransmission.removeAll(completed);

    // we check the lifetime for each running containers
    ContainerSimulator cs = null;
    synchronized(completedContainerList) {
      while ((cs = containerQueue.poll()) != null) {
        runningContainers.remove(cs.getAssignedContainer().getId());
        completedContainerList.add(cs.getAssignedContainer().getId());
        LOG.debug(MessageFormat.format("Container {0} has completed",
                cs.getAssignedContainer().getId()));
      }
    }
    
    // send heart beat
    NodeHeartbeatRequest beatRequest =
            Records.newRecord(NodeHeartbeatRequest.class);
    beatRequest.setLastKnownNMTokenMasterKey(masterKey);
    NodeStatus ns = Records.newRecord(NodeStatus.class);
    
    ns.setContainersStatuses(generateContainerStatusList());
    ns.setNodeId(node.getNodeID());
    ns.setKeepAliveApplications(new ArrayList<ApplicationId>());
    ns.setResponseId(RESPONSE_ID ++);
    ns.setNodeHealthStatus(NodeHealthStatus.newInstance(true, "", 0));
    beatRequest.setNodeStatus(ns);
    NodeHeartbeatResponse beatResponse =
        rm.getResourceTrackerService().nodeHeartbeat(beatRequest);
    if (! beatResponse.getContainersToCleanup().isEmpty()) {
      // remove from queue
      synchronized(releasedContainerList) {
        for (ContainerId containerId : beatResponse.getContainersToCleanup()){
          if (amContainerList.contains(containerId)) {
            // AM container (not killed?, only release)
            synchronized(amContainerList) {
              amContainerList.remove(containerId);
            }
            LOG.debug(MessageFormat.format("NodeManager {0} releases " +
                "an AM ({1}).", node.getNodeID(), containerId));
          } else {
            cs = runningContainers.remove(containerId);
            containerQueue.remove(cs);
            containersWaitingForTransmission.remove(cs);
            releasedContainerList.add(containerId);
            LOG.debug(MessageFormat.format("NodeManager {0} releases a " +
                "container ({1}).", node.getNodeID(), containerId));
          }
        }
      }
    }
    if (beatResponse.getNodeAction() == NodeAction.SHUTDOWN) {
      lastStep();
    }
  }

  @Override
  public void lastStep() {
    // do nothing
  }

  /**
   * catch status of all containers located on current node
   */
  private ArrayList<ContainerStatus> generateContainerStatusList() {
    ArrayList<ContainerStatus> csList = new ArrayList<ContainerStatus>();
    // add running containers
    for (ContainerSimulator container : runningContainers.values()) {
      csList.add(newContainerStatus(container.getAssignedContainer().getId(),
        ContainerState.RUNNING, ContainerExitStatus.SUCCESS));
    }
    synchronized(amContainerList) {
      for (ContainerId cId : amContainerList) {
        csList.add(newContainerStatus(cId,
            ContainerState.RUNNING, ContainerExitStatus.SUCCESS));
      }
    }
    // add complete containers
    synchronized(completedContainerList) {
      for (ContainerId cId : completedContainerList) {
        LOG.debug(MessageFormat.format("NodeManager {0} completed" +
                " container ({1}).", node.getNodeID(), cId));
        csList.add(newContainerStatus(
                cId, ContainerState.COMPLETE, ContainerExitStatus.SUCCESS));
      }
      completedContainerList.clear();
    }
    // released containers
    synchronized(releasedContainerList) {
      for (ContainerId cId : releasedContainerList) {
        LOG.debug(MessageFormat.format("NodeManager {0} released container" +
                " ({1}).", node.getNodeID(), cId));
        csList.add(newContainerStatus(
                cId, ContainerState.COMPLETE, ContainerExitStatus.ABORTED));
      }
      releasedContainerList.clear();
    }
    return csList;
  }

  private ContainerStatus newContainerStatus(ContainerId cId, 
                                             ContainerState state,
                                             int exitState) {
    ContainerStatus cs = Records.newRecord(ContainerStatus.class);
    cs.setContainerId(cId);
    cs.setState(state);
    cs.setExitStatus(exitState);
    return cs;
  }

  public RMNode getNode() {
    return node;
  }

  /**
   * launch a ContainerSimulator on a newly allocated Container.
   *
   * @param container Allocated container
   * @param cs Container simulator. If cs is null the container is an AM, else it is a map/reduce.
   */
  public void addNewContainer(Container container, ContainerSimulator cs) {
    LOG.debug(MessageFormat.format("NodeManager {0} launches a new " +
            "container ({1}).", node.getNodeID(), container.getId()));
    if (cs == null) {
      // AM container
      synchronized(amContainerList) {
        amContainerList.add(container.getId());
      }
    } else {
      // normal container
      cs.setAssignedContainer(container);
      containersWaitingForTransmission.add(cs);
      containerQueue.add(cs);
      runningContainers.put(cs.getAssignedContainer().getId(), cs);
      cs.startTransmission(subscriptionKey);
    }
  }

  /**
   * clean up an AM container and add to completed list
   * @param containerId id of the container to be cleaned
   */
  public void cleanupContainer(ContainerId containerId) {
    synchronized(amContainerList) {
      amContainerList.remove(containerId);
    }
    synchronized(completedContainerList) {
      completedContainerList.add(containerId);
    }
  }
}
