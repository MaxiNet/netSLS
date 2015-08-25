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
package org.apache.hadoop.yarn.sls.networkemulator;

import com.googlecode.jsonrpc4j.JsonRpcHttpClient;
import org.apache.hadoop.yarn.sls.SLSRunner;
import org.apache.hadoop.yarn.sls.conf.SLSConfiguration;
import org.apache.log4j.Logger;

import java.net.MalformedURLException;
import java.net.URL;
import java.util.HashMap;
import java.util.Map;

public class NetworkEmulatorClient {
  // logger
  public final static Logger LOG = Logger.getLogger(NetworkEmulatorClient.class);

  private JsonRpcHttpClient rpcClient;

  public NetworkEmulatorClient() {
    try {
      rpcClient = new JsonRpcHttpClient(new URL(SLSRunner.getInstance().getConf().get(SLSConfiguration.NETWORKEMULATOR_RPC_URL)));
    } catch (MalformedURLException e) {
      e.printStackTrace();
    }
  }

  public Boolean startEmulation(Topology topology) throws Throwable {
    LOG.info("Invoking start_emulation");
    return rpcClient.invoke("start_emulation", new Object[]{topology.toJson()}, Boolean.class);
  }

  public String registerCoflow() throws Throwable {
    LOG.info("Invoking register_coflow");
    // TODO: Replace dummy by read coflow description
    Map<String, String> dummy = new HashMap<String, String>();
    dummy.put("coflow_description", "");
    return rpcClient.invoke("register_coflow", dummy, String.class);
  }

  public Boolean unregisterCoflow(String coflowId) throws Throwable {
    LOG.info("Invoking unregister_coflow");
    return rpcClient.invoke("unregister_coflow", new Object[]{coflowId}, Boolean.class);
  }

  public Integer transmitNBytes(String coflowId, String source, String destination, Long nBytes,
      String subscriptionKey) throws Throwable {
    LOG.info("Invoking transmit_n_bytes with coflowId: " + coflowId
        + ", source: " + source
        + ", destination: " + destination
        + ", n_bytes: " + nBytes.toString()
        + ", subscription_key: " + subscriptionKey);
    return rpcClient.invoke("transmit_n_bytes", new Object[]{coflowId, source, destination, nBytes, subscriptionKey},
        Integer.class);
  }
}
