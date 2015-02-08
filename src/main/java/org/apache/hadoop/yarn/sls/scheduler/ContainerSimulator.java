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

package org.apache.hadoop.yarn.sls.scheduler;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Delayed;
import java.util.concurrent.TimeUnit;

import org.apache.hadoop.classification.InterfaceAudience.Private;
import org.apache.hadoop.classification.InterfaceStability.Unstable;
import org.apache.hadoop.yarn.api.records.ApplicationId;
import org.apache.hadoop.yarn.api.records.Container;
import org.apache.hadoop.yarn.api.records.Resource;
import org.apache.hadoop.yarn.sls.SLSRunner;
import org.apache.hadoop.yarn.sls.appmaster.AMSimulator;
import org.apache.hadoop.yarn.sls.appmaster.MRAMSimulator;
import org.apache.hadoop.yarn.sls.networksimulator.NetworkSimulatorClient;
import org.apache.hadoop.yarn.sls.utils.SLSUtils;

@Private
@Unstable
public class ContainerSimulator implements Delayed {
  /**
   * Resource allocated.
   */
  private Resource resource;

  /**
   * End time.
   */
  private long endTime;

  /**
   * Life time (ms).
   */
  private long lifeTime;

  /**
   * Hostname to request. The AM requests a container for this ContainerSimulator on this particular host.
   */
  private String hostname;

  /**
   * Container priority.
   */
  private int priority;

  /**
   * Task type simulated by this ContainerSimulator. Either "map" or "reduce".
   */
  private String type;

  /**
   * Container assigned by AM.
   */
  private Container assignedContainer;

  /**
   * Number of bytes read by this task (map and reduce only).
   */
  private long inputBytes;

  /**
   * Number of bytes written by this task (map and reduce only).
   */
  private long outputBytes;

  /**
   * Location of input splits (map only).
   */
  private List<String> splitLocations;

  /**
   * List of transmission ids of open transmission.
   */
  private List<Integer> openTransmissions;

  public ContainerSimulator(Resource resource, long lifeTime, String hostname, int priority, String type,
      long inputBytes, long outputBytes, List<String> splitLocations) {
    this.resource = resource;
    this.lifeTime = lifeTime;
    this.hostname = hostname;
    this.priority = priority;
    this.type = type;
    this.inputBytes = inputBytes;
    this.outputBytes = outputBytes;
    this.splitLocations = splitLocations;
    this.endTime = Long.MAX_VALUE;
    this.openTransmissions = new ArrayList<Integer>();
  }

  /**
   * Starts the work phase at the current time.
   */
  public void startWork() {
    this.endTime = lifeTime + System.currentTimeMillis();
  }

  /**
   * Starts the transmission phase.
   *
   * During the transmission phase map tasks fetch their input split and reduce tasks fetch the intermediate data,
   * respectively.
   */
  public void startTransmission(String subscriptionKey) {
    // TODO: move to separate function
    ApplicationId applicationId = assignedContainer.getId().getApplicationAttemptId().getApplicationId();
    MRAMSimulator amSimulator = null;
    for (AMSimulator amSim : SLSRunner.getInstance().getAmMap().values()) {
      if (! (amSim instanceof MRAMSimulator)) {
        continue;
      }
      if (((MRAMSimulator) amSim).getAmContainer().getId().getApplicationAttemptId().getApplicationId()
          .equals(applicationId)) {
        amSimulator = (MRAMSimulator) amSim;
        break;
      }
    }

    NetworkSimulatorClient nsClient = new NetworkSimulatorClient();
    String coflowId = amSimulator.getCoflowId();
    String destination = assignedContainer.getNodeId().getHost();
    if (type.equals("map")) {
      // Skip if data-local
      for (String host : splitLocations) {
        if (SLSUtils.getRackHostName(host)[1].equals(destination)) {
          return;
        }
      }
      // TODO: calculate "nearest" split
      String source = SLSUtils.getRackHostName(splitLocations.get(0))[1];

      try {
        Integer transmissionId = nsClient.transmitNBytes(coflowId, source, destination, inputBytes, subscriptionKey);
        openTransmissions.add(transmissionId);
      } catch (Throwable t) {
        throw new RuntimeException(t);
      }
    } else {
      for(ContainerSimulator cs : amSimulator.getAllMaps()) {
        String source = cs.getAssignedContainer().getNodeId().getHost();
        // Skip if data-local
        if (source.equals(destination)) {
          continue;
        }

        try {
          Integer transmissionId = nsClient.transmitNBytes(coflowId, source, destination,
              (long) (inputBytes / amSimulator.getAllMaps().size()), subscriptionKey);
          openTransmissions.add(transmissionId);
        } catch (Throwable t) {
          throw new RuntimeException(t);
        }
      }
    }

    // If transmission does not complete or call back for some reason finish ContainerSimulator anyways.
    this.endTime = System.currentTimeMillis() + this.lifeTime * 50;
  }

  /**
   * Call when a transmission is completed to update list of open transmissions.
   * @param transmissionId Id of completed transmission.
   */
  public void notifyTransmissionCompleted(Integer transmissionId) {
    openTransmissions.remove(transmissionId);
  }

  /**
   * Checks if all transmissions of this task are completed.
   */
  public boolean isAllTransmissionsCompleted() {
    return openTransmissions.isEmpty();
  }

  @Override
  public int compareTo(Delayed o) {
    if (!(o instanceof ContainerSimulator)) {
      throw new IllegalArgumentException(
              "Parameter must be a ContainerSimulator instance");
    }
    ContainerSimulator other = (ContainerSimulator) o;
    return (int) Math.signum(endTime - other.endTime);
  }

  @Override
  public long getDelay(TimeUnit unit) {
    return unit.convert(endTime - System.currentTimeMillis(),
          TimeUnit.MILLISECONDS);
  }

  public Container getAssignedContainer() {
    return assignedContainer;
  }

  public void setAssignedContainer(Container assignedContainer) {
    this.assignedContainer = assignedContainer;
  }

  public String getHostname() {
    return hostname;
  }

  public int getPriority() {
    return priority;
  }

  public void setPriority(int p) {
    priority = p;
  }

  public Resource getResource() {
    return resource;
  }

  public String getType() {
    return type;
  }
}
