#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Daniel Bernal <dbernal_ext@amco.mx>"
#Date Created since 2018, JUN.

import os, sys, json
import boto3
import time
import argparse
from subprocess import call



class aws_autoscaling_rollout():
    
    def __init__(self, args):
        self.autoscaler = None
        self.args = args
        self.min_size = 0
        self.max_size = 0
        self.desired_size = 0
        self.min_desired_temp=0
        self.cnt_instance = 0
        self.old_instances = []
        try:
            self.autoscaling = boto3.client('autoscaling')
        except:
            self.autoscaling = boto3.client('autoscaling', region_name=self.args.region)
        
    def getAutoescaler(self, groupName):
        returnData = []
        try:
            data = self.autoscaling.describe_auto_scaling_groups(
                AutoScalingGroupNames = [
                    groupName,
                ],
                MaxRecords = 1
            )
            if 'AutoScalingGroups' in data:
                returnData = data['AutoScalingGroups'][0] if len (data['AutoScalingGroups']) >0 else []
        except Exception as ex:
            raise Exception("Error Autoscaling group not found [ %s ]. Exception: %s" %(groupName, ex))

        return returnData

    def getInstancesAutoScaling(self, autoscaler):
        
        if autoscaler is str:
            autoscaler = self.getAutoescaler(autoscaler)
        if autoscaler is None:
            raise Exception("No AutoScaler set yet.")
            return []
        
        
        self.old_instances =  autoscaler['Instances'] if 'Instances' in autoscaler else []

        return self.old_instances

    
    def setInfoAutoScaler(self, autoscaler):
        infoSetter = dict()
        if autoscaler is str:
            autoscaler = self.getAutoescaler(autoscaler)
        if autoscaler is None:
            raise Exception("No AutoScaler set yet.")
            return []

        try: self.max_size = int(autoscaler['MaxSize']) #Maxima
        except: self.max_size = 0
        
        try: self.desired_size = int(autoscaler['DesiredCapacity']) #Deseadas
        except: self.desired_size = 0
        try: self.min_size = int(autoscaler['MinSize']) #Minima
        except: self.min_size = 0
        
        try: 
            self.cnt_instance = int(len(self.getInstancesAutoScaling(self.autoscaler)))
        except:
            self.cnt_instance = 0

        if self.cnt_instance > 0 :
            self.min_desired_temp = self.cnt_instance * 2

        infoSetter['MaxSize'] = int(self.min_desired_temp +1) if self.min_desired_temp > self.max_size else self.max_size
        infoSetter['MinSize'] =  int(self.min_desired_temp)
        infoSetter['DesiredCapacity'] =  int(self.min_desired_temp)
        self.updatePolicitiesAutoScaling(self.args.name, ['OldestInstance','OldestLaunchConfiguration'] )
        return self.updateSettingsAutoScaling(self.args.name, infoSetter)
    
    def updateSettingsAutoScaling(self, group_name, infoSetter ):
       
        response = self.autoscaling.update_auto_scaling_group(
            AutoScalingGroupName=group_name,
            MaxSize=infoSetter['MaxSize'],
            MinSize=infoSetter['MinSize'],
            DesiredCapacity=infoSetter['DesiredCapacity']
        )
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            return True
        else:
            print("Error when try update info autoscaling group, please review yours credentials")
            return False
    def updatePolicitiesAutoScaling(self, group_name, terms):
        response = self.autoscaling.update_auto_scaling_group(
            AutoScalingGroupName=group_name,
            TerminationPolicies=terms            
        )
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            return True
        else:
            print("Error when try update info autoscaling group, please review yours credentials")
            return False

    def getAutoescalerIntancesHaveHealthy(self, autoscaler):
        healthy = []
        if autoscaler is str:
            autoscaler = self.getAutoescaler(autoscaler)
        if autoscaler is None:
            raise Exception("No AutoScaler set yet.")
            return []

        for instance in autoscaler['Instances']:
            if instance['HealthStatus'] == 'Healthy':
                healthy.append(instance)
        return healthy

    def getAutoscalerProgressStatus( self, group_name ):
        autoscaler = self.autoscaling.describe_auto_scaling_groups(
            AutoScalingGroupNames=[
                group_name,
            ],
            MaxRecords=1
        )
        if len(autoscaler['AutoScalingGroups']) != 1:
            print("Error unable to get describe autoscaling: [ %s ]" %(group_name))
            exit(1)
        autoscaler = autoscaler['AutoScalingGroups'][0]

        healthy_instance = int(len(self.getAutoescalerIntancesHaveHealthy( autoscaler )))
        if healthy_instance != autoscaler['DesiredCapacity']:
            print ("INFO: Our autoscaler must be scaling, desired %s, healthy %s" %(autoscaler['DesiredCapacity'], healthy_instance))
            return False

        return True
        
    def waitAutoscalerWithNewInstancesHealthy(self, group_name):
        instances = self.getInstancesAutoScaling(self.autoscaler)
        if instances is None:
            raise Exception("Error get Instances for autoscaling [ %s ]" %(group_name))
        
        while True:
            instancesReady = int(len(self.getAutoescalerIntancesHaveHealthy(self.autoscaler)))
            if len(instances) != instancesReady:
                print("WARN: Autoscaling in progress: %s to %s" %(instancesReady, len(instances)))
            elif self.getAutoscalerProgressStatus(self.args.name) is False:
                print("WARN: Autoscaling currently performing, we should wait...")
            else:
                print("SUCCESS: Autoscaling ready, desired is %s to %s" %(instancesReady, len(instances) ))
                break
            print("Waiting 3 seconds...")
            
            time.sleep(3)
        return True

    def run(self):
        self.autoscaler = self.getAutoescaler(self.args.name)
        if self.autoscaler is False:
            print("Error Autoscaling not set")
            exit(1)
        
        if self.setInfoAutoScaler(self.autoscaler):
            self.waitAutoscalerWithNewInstancesHealthy(self.args.name)
            OldInfo = dict()
            OldInfo['MaxSize'] = self.max_size
            OldInfo['MinSize'] = self.min_size
            OldInfo['DesiredCapacity'] = self.desired_size

            if self.updateSettingsAutoScaling(self.args.name, OldInfo):
                print("All Success.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AutoScaling for DLA Services")

    parser.add_argument('--name', help="auto-scaling-group Name")
    parser.add_argument('--region', help="name of region")

    args = parser.parse_args()
    print(args)
    app = aws_autoscaling_rollout(args)

    app.run()
