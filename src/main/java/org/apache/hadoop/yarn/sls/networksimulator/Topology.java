/**
 * Copyright 2015 Malte Splietker
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.hadoop.yarn.sls.networksimulator;

import org.apache.hadoop.yarn.server.resourcemanager.rmnode.RMNode;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

public class Topology {
  private Map<String, Rack> racks;

  private String type = "Clos";

  public Topology(Set<RMNode> nodes) {
    racks = new HashMap<String, Rack>();

    for (RMNode node : nodes) {
      String rackname = node.getRackName();
      if (!racks.containsKey(rackname)) {
        racks.put(rackname, new Rack(rackname));
      }
      racks.get(rackname).addHost(node.getHostName());
    }
  }

  public Object toJson() {
    Map<String, Object> arguments = new HashMap<String, Object>();
    arguments.put("racks", new HashSet<Object>());
    for (Rack rack : racks.values()) {
      ((Set<Object>) arguments.get("racks")).add(rack.toJsonObject());
    }

    HashMap<String, Object> jsonObject = new HashMap<String, Object>();
    jsonObject.put("type", type);
    jsonObject.put("arguments", arguments);

    return jsonObject;
  }

  private static class Rack {
    private Set<String> hosts;

    private String id;

    public Rack(String id) {
      hosts = new HashSet<String>();
      this.id = id;
    }

    public void addHost(String host) {
      hosts.add(host);
    }

    public Object toJsonObject() {
      Map<String, Object> jsonObject = new HashMap<String, Object>();

      jsonObject.put("id", id);
      jsonObject.put("hosts", hosts);

      return jsonObject;
    }
  }
}
