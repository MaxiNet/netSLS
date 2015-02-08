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
package org.apache.hadoop.yarn.sls.statistics;

import java.io.*;

/**
 * Logs the number of recently completed tasks in regular intervals to a text file.
 *
 * The logger only remembers the count since the last write, so the counter is reset with every write.
 */
public class CompletedTasksLogger implements Runnable {
  /**
   * File to write to.
   */
  private File logFile;

  /**
   * Logging interval in ms.
   */
  private long interval;

  /**
   * Counter.
   */
  private Integer counter;

  public CompletedTasksLogger(File logFile, long interval) {
    this.logFile = logFile;
    this.interval = interval;
    this.counter = 0;
  }

  @Override
  public void run() {
    PrintWriter fw = null;
    try {
      while (true) {
        long intervalStartTime = System.currentTimeMillis();
        // Reopen to truncate file
        fw = new PrintWriter(logFile);
        synchronized (counter) {
          fw.print(this.counter / (this.interval / 1000.0));  //wir geben completedTasks/s aus.
          this.counter = 0;
        }
        fw.close();

        // Sleep till next interval
        long currentTime = System.currentTimeMillis();
        while (currentTime - intervalStartTime < interval) {
          try {
            Thread.sleep(interval - (currentTime - intervalStartTime));
          } catch (InterruptedException e) { }
          currentTime = System.currentTimeMillis();
        }
      }
    } catch (FileNotFoundException e) {
      throw new RuntimeException(e);
    } finally {
      if (fw != null) {
        fw.close();
      }
    }
  }

  /**
   * Increments counter by given amount.
   * @param amount Increment counter by this.
   */
  public synchronized void incrementCounter(int amount) {
    this.counter += amount;
  }
}
