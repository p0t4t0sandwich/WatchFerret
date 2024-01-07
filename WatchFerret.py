from __future__ import annotations

from datetime import datetime
from threading import Thread
from time import sleep
import yaml
import os

from ampapi.modules.ADS import ADS
from ampapi.modules.CommonAPI import CommonAPI


class WatchFerret():
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.instance_dict: dict = {}

        # Get host, username, password from config
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
            f.close()

        self.host = config["global"]["host"]
        self.username = config["global"]["username"]
        self.password = config["global"]["password"]

        self.restart_tracker: dict = {}
        self.start_tracker: dict = {}
        self.stop_tracker: dict = {}

    # Logger
    def logger(self, logging_path: str, instance_name: str, string: str) -> None:
        time = datetime.now()
        today = str(time.strftime("%Y-%m-%d"))
        now = str(time.strftime("%d/%m/%Y %H:%M:%S"))

        if logging_path[-1] == "/":
            folder = logging_path
        else:
            folder = logging_path + "/"

        if not os.path.exists(folder):
            os.makedirs(folder)

        log_name = f"{folder}{instance_name}-{today}.log"

        try:
            file = open(log_name, "a")
        except:
            file = open(log_name, "w")
            file.close()
            file = open(log_name, "a")
        file.write("[" + now + "]: [" + instance_name + " Log] " + string + "\n")
        print("[" + now + "]: [" + instance_name + " Log] " + string)
        file.close()

    # Get Config
    def get_config(self, instance_name: str) -> dict:
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
            f.close()

        try:
            return dict(config["global"], **config["instances"][instance_name])
        except:
            print("Config Error, instance not found in config")
            return {}

    # Instance Type
    class Instance:
        def __init__(self, name: str = None, id: str = None, API: CommonAPI = None):
            self.name = name
            self.id = id
            self.API = API

    # Instance Login
    def instanceLogin(self, instance: Instance) -> bool:
        if instance.name != None:
            # Get Instance ID
            if (instance.id == None):
                # Loop through the targets
                for target in self.ADS.ADSModule.GetInstances():

                    # Loop through the target instances
                    for inst in target.AvailableInstances:
                        instanceModule: str = inst.Module

                        # Check if the instance is a Minecraft instance and grab the instance id
                        if instanceModule == "Minecraft":
                            instanceName: str = inst.InstanceName
                            if instanceName == instance.name:
                                id: str = inst.InstanceID

                                # Save id back to config file
                                try:
                                    with open("./config.yml", 'r') as f:
                                        config = yaml.safe_load(f)
                                        f.close()

                                    config["instances"][instanceName]["id"] = id

                                    with open("./config.yml", 'w') as f:
                                        yaml.dump(config, f, default_flow_style=False)
                                        f.close()
                                except:
                                    print("Error writing instance id to config file")

                                instance.id = id
                                break

                        # Break if instance id is found
                        if instance.id != None:
                            break

            instance.API = self.ADS.InstanceLogin(instance.id, "Minecraft")

            if instance.API != None:
                self.instance_dict[instance.name] = instance
                return True

        return False

    # Monitor
    def monitor(self, serverName: str):
        if serverName not in self.restart_tracker.keys():
            self.restart_tracker[serverName] = 0
            self.start_tracker[serverName] = 0
            self.stop_tracker[serverName] = 0

        while True:
            instance_conf = self.get_config(serverName)
            try:
                # Get Server State
                status = self.instance_dict[serverName].API.Core.GetStatus().State
                restart_threshold = instance_conf["restart_threshold"]
                start_threshold = instance_conf["start_threshold"]
                stop_threshold = instance_conf["stop_threshold"]

                message = f"Server Status: {status}"

                if restart_threshold != -1 and status == 30:
                    self.restart_tracker[serverName] += 1
                    self.start_tracker[serverName] = 0
                    self.stop_tracker[serverName] = 0
                    message += f", Restart Pings: {self.restart_tracker[serverName]}"
                elif start_threshold != -1 and status == 10:
                    self.start_tracker[serverName] += 1
                    self.restart_tracker[serverName] = 0
                    self.stop_tracker[serverName] = 0
                    message += f", Start Pings: {self.start_tracker[serverName]}"
                elif stop_threshold != -1 and status == 40:
                    self.stop_tracker[serverName] += 1
                    self.restart_tracker[serverName] = 0
                    self.start_tracker[serverName] = 0
                    message += f", Stop Pings: {self.stop_tracker[serverName]}"
                else:
                    self.restart_tracker[serverName] = 0
                    self.start_tracker[serverName] = 0
                    self.stop_tracker[serverName] = 0

                self.logger(instance_conf["logging_path"], serverName, message)

                if restart_threshold != -1 and self.restart_tracker[serverName] >= restart_threshold:
                    self.logger(instance_conf["logging_path"], serverName, f"Watchdog Event Detected On Server Restart")
                    self.restart_tracker[serverName] = 0
                    self.instance_dict[serverName].API.Core.Kill()
                    sleep(10)
                    self.instance_dict[serverName].API.Core.Start()
                    self.logger(instance_conf["logging_path"], serverName, f"Attempting to rescue: {serverName}")
                elif start_threshold != -1 and self.start_tracker[serverName] >= start_threshold:
                    self.logger(instance_conf["logging_path"], serverName, f"Watchdog Event Detected On Server Start")
                    self.start_tracker[serverName] = 0
                    self.instance_dict[serverName].API.Core.Kill()
                    sleep(10)
                    self.instance_dict[serverName].API.Core.Start()
                    self.logger(instance_conf["logging_path"], serverName, f"Attempting to rescue: {serverName}")
                elif stop_threshold != -1 and self.stop_tracker[serverName] >= stop_threshold:
                    self.logger(instance_conf["logging_path"], serverName, f"Watchdog Event Detected On Server Stop")
                    self.stop_tracker[serverName] = 0
                    self.instance_dict[serverName].API.Core.Kill()
                    sleep(10)
                    self.instance_dict[serverName].API.Core.Start()
                    self.logger(instance_conf["logging_path"], serverName, f"Attempting to rescue: {serverName}")

            # On error, try to re-authenticate with AMP
            except Exception as e:
                instance: self.Instance = self.instance_dict[serverName]
                result: bool = self.instanceLogin(instance)
                if result == True:
                    self.logger(instance_conf["logging_path"], serverName, f"Re-Authenticating with AMP\n{e}")
                else:
                    self.logger(instance_conf["logging_path"], serverName, f"an error occured while re-authenticating with AMP\n{e}")

            sleep(instance_conf["sample_interval"])

    # Start
    def start(self) -> None:
        self.ADS = ADS(self.host, self.username, self.password)
        self.ADS.Login()

        # Get instances from config file
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
            f.close()

        for serverName in config["instances"].keys():
            # Get instance name and id
            name: str = config["instances"][serverName]["name"]
            id: str = config["instances"][serverName]["id"] if "id" in config["instances"][serverName].keys() else None

            instance: self.Instance = self.Instance(name, id)
            status: bool = self.instanceLogin(instance)
            if status == True:
                print(f"Instance {instance.name} is online!")
                Thread(target=self.monitor, args=(serverName,)).start()
            else:
                print(f"Instance {instance.name} is offline!")


if __name__ == "__main__":
    wf = WatchFerret("./config.yml")
    wf.start()
