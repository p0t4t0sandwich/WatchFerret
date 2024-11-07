from __future__ import annotations

from datetime import datetime
from threading import Thread
from time import sleep
import yaml
import os

from ampapi.auth import RefreshingAuthProvider
from ampapi.modules import ADS, CommonAPI

class WatchFerret():
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.instnaces: dict[str, CommonAPI] = {}

        # Get host, username, password from config
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
            f.close()

        self.host = config["global"]["host"]
        if self.host[-1] != "/":
            self.host += "/"
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

    # Instance Login
    def instanceLogin(self, instanceName: str, serverName: str) -> bool:
        if instanceName != None:
            self.instnaces[serverName] = CommonAPI(
                RefreshingAuthProvider(
                    panelUrl=f"{self.host}API/ADSModule/Servers/{instanceName}/",
                    username=self.username,
                    password=self.password
            ))
            try:
                return self.instnaces[serverName]._authprovider.Login().success
            except:
                return False
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
                status_enum = self.instnaces[serverName].Core.GetStatus().State
                status = status_enum.value
                restart_threshold = instance_conf["restart_threshold"]
                start_threshold = instance_conf["start_threshold"]
                stop_threshold = instance_conf["stop_threshold"]

                message = f"Server Status: {status_enum.name} ({status})"

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
                    self.instnaces[serverName].Core.Kill()
                    sleep(10)
                    self.instnaces[serverName].Core.Start()
                    self.logger(instance_conf["logging_path"], serverName, f"Attempting to rescue: {serverName}")
                elif start_threshold != -1 and self.start_tracker[serverName] >= start_threshold:
                    self.logger(instance_conf["logging_path"], serverName, f"Watchdog Event Detected On Server Start")
                    self.start_tracker[serverName] = 0
                    self.instnaces[serverName].Core.Kill()
                    sleep(10)
                    self.instnaces[serverName].Core.Start()
                    self.logger(instance_conf["logging_path"], serverName, f"Attempting to rescue: {serverName}")
                elif stop_threshold != -1 and self.stop_tracker[serverName] >= stop_threshold:
                    self.logger(instance_conf["logging_path"], serverName, f"Watchdog Event Detected On Server Stop")
                    self.stop_tracker[serverName] = 0
                    self.instnaces[serverName].Core.Kill()
                    sleep(10)
                    self.instnaces[serverName].Core.Start()
                    self.logger(instance_conf["logging_path"], serverName, f"Attempting to rescue: {serverName}")

            # On error, try to re-authenticate with AMP
            except Exception as e:
                result: bool = self.instnaces[serverName]._authprovider.Login().success
                if result == True:
                    self.logger(instance_conf["logging_path"], serverName, f"Re-Authenticating with AMP\n{e}")
                else:
                    self.logger(instance_conf["logging_path"], serverName, f"an error occured while re-authenticating with AMP\n{e}")

            sleep(instance_conf["sample_interval"])

    # Start
    def start(self) -> None:
        auth_provider = RefreshingAuthProvider(
            panelUrl=self.host,
            username=self.username,
            password=self.password
        )
        self.ADS = ADS(auth_provider)

        # Get instances from config file
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
            f.close()

        for serverName in config["instances"].keys():
            # Get instance name and id
            name: str = config["instances"][serverName]["name"]
            status: bool = self.instanceLogin(name, serverName)
            if status == True:
                print(f"Instance {name} is online!")
                Thread(target=self.monitor, args=(serverName,)).start()
            else:
                print(f"Instance {name} is offline!")


if __name__ == "__main__":
    wf = WatchFerret("./config.yml")
    wf.start()
