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
            self.ec2 = boto3.client("ec2")
            self.elb = boto3.client("elb")
            self.elbv2 = boto3.client("elbv2")
        except:
            self.autoscaling = boto3.client('autoscaling', region_name=self.args.region)
            self.ec2 = boto3.client("ec2", region_name=self.args.region)
            self.elb = boto3.client("elb", region_name=self.args.region)
            self.elbv2 = boto3.client("elbv2", region_name=self.args.region)
        
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
            raise Exception("ERROR: Autoscaling group not found [ %s ]. Exception: %s" %(groupName, ex))
        
        if (self.args.debug=="verbose"): print("DEBUG: %s. RETURN: %s " %(sys._getframe().f_code.co_name,returnData))
        return returnData

    def getInstancesAutoScaling(self, autoscaler):
        
        if autoscaler is str:
            autoscaler = self.getAutoescaler(autoscaler)
        if autoscaler is None:
            raise Exception("No AutoScaler set yet.")

        
        self.old_instances = old_instances = []
        old_instances =  autoscaler['Instances'] if 'Instances' in autoscaler else []
        [ self.old_instances.append(instance) for instance in old_instances if instance['LifecycleState'] != 'Terminating' ]
        if (self.args.debug=="verbose"): print("DEBUG: %s. RETURN: %s " %(sys._getframe().f_code.co_name,self.old_instances))
        return self.old_instances
    

    def setInfoAutoScaler(self, autoscaler):
        infoSetter = dict()
        if autoscaler is str:
            autoscaler = self.getAutoescaler(autoscaler)
        if autoscaler is None:
            raise Exception("No AutoScaler set yet.")


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
        policities = self.updatePolicitiesAutoScaling(self.args.name, ['OldestInstance','OldestLaunchConfiguration'] )
        protected  = self.upateInstancesProtectedFromScaleIn(self.args.name, autoscaler)
        processes  = self.updateAutoScalingSuspendedProcesses(self.args.name, self.autoscaling)
        infoASG    = self.updateSettingsAutoScaling(self.args.name, infoSetter)
        if (self.args.debug=="verbose"): print("DEBUG: %s. RETURN: Setting Policities: [ %s ].  ProtectedFromScaleIn [ %s ]. SuspendedProcesses: [ %s ]. SettingsAutoScaling [ %s ]" %(sys._getframe().f_code.co_name,policities, protected, processes, infoASG))
        
        return infoASG

    def updateAutoScalingSuspendedProcesses(self, group_name, autoscaler):
        if autoscaler is str:
            autoscaler = self.getAutoescaler(autoscaler)
        if autoscaler is None:
            raise Exception("No AutoScaler set yet.")
        try:
            autoscaler.resume_processes(
                AutoScalingGroupName=group_name,
            )
        except Exception as e:
            print("WARNING: Can't remove ScalingProcess == Terminate on Suspend_process. TRACE: %s" %(e))
        return True
    
    def upateInstancesProtectedFromScaleIn(self, group_name, autoscaler):
        if autoscaler is str:
            autoscaler = self.getAutoescaler(autoscaler)
        if autoscaler is None:
            raise Exception("No AutoScaler set yet.")

        instances = []
        [ instances.append(x['InstanceId']) for x in self.getInstancesAutoScaling(autoscaler) ] 

        response = self.autoscaling.set_instance_protection(
            AutoScalingGroupName=group_name,
            InstanceIds=instances,
            ProtectedFromScaleIn=False,
        )
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            return True
        else:
            print("ERROR: when try update ProtectedFromScaleIn in Instances, please review yours credentials")
            return False
    

        
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
            print("ERROR: when try update info autoscaling group, please review yours credentials")
            return False
    def updatePolicitiesAutoScaling(self, group_name, terms):
        response = self.autoscaling.update_auto_scaling_group(
            AutoScalingGroupName=group_name,
            TerminationPolicies=terms            
        )
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            return True
        else:
            print("ERROR: when try update info autoscaling group, please review yours credentials")
            return False

    def getAutoescalerIntancesHaveHealthy(self, autoscaler):
        healthy = []
        if autoscaler is str:
            autoscaler = self.getAutoescaler(autoscaler)
        if autoscaler is None:
            raise Exception("No AutoScaler set yet.")


        for instance in autoscaler['Instances']:
            if instance['LifecycleState'] == 'InService':
                healthy.append(instance)
        if (self.args.debug=="verbose"): print("DEBUG: %s. RETURN: %s" %(sys._getframe().f_code.co_name,healthy))
        return healthy

    def getAutoscalerProgressStatus( self, group_name ):
        autoscaler = self.autoscaling.describe_auto_scaling_groups(
            AutoScalingGroupNames=[
                group_name,
            ],
            MaxRecords=1
        )
        if len(autoscaler['AutoScalingGroups']) != 1:
            print("ERROR: unable to get describe autoscaling: [ %s ]" %(group_name))
            exit(1)
        autoscaler = autoscaler['AutoScalingGroups'][0]

        healthy_instance = int(len(self.getAutoescalerIntancesHaveHealthy( autoscaler )))
        if healthy_instance != autoscaler['DesiredCapacity']:
            print ("INFO: Our autoscaler must be scaling, desired %s, healthy %s" %(autoscaler['DesiredCapacity'], healthy_instance))
            return False

        return True
        
    def waitAutoscalerWithNewInstancesHealthy(self, group_name):
        instances = self.getInstancesAutoScaling(self.getAutoescaler(self.args.name))
        if (self.args.debug=="critical"): print("DEBUG: %s. RETURN: %s" %("instances",instances))

        if instances is None:
            raise Exception("ERROR: get Instances for autoscaling [ %s ]" %(group_name))
        
        while True:
            instances = self.getInstancesAutoScaling(self.getAutoescaler(self.args.name))
            if (self.args.debug=="critical"): print("DEBUG: %s. RETURN: %s" %("instancesTotal",instances))
            
            instancesReady = int(len(self.getAutoescalerIntancesHaveHealthy(self.getAutoescaler(self.args.name))))
            if (self.args.debug=="critical"): print("DEBUG: %s. RETURN: %s" %("instancesReady",self.getAutoescalerIntancesHaveHealthy(self.autoscaler)))

            if len(instances) != instancesReady:
                print("WARNING: Autoscaling in progress: %s to %s" %(instancesReady, len(instances)))
            elif self.getAutoscalerProgressStatus(self.args.name) is False:
                print("WARNING: Autoscaling currently performing, we should wait...")
            else:
                print("SUCCESS: Autoscaling ready, desired is %s to %s" %(self.autoscaler['DesiredCapacity'], len(instances) ))
                break
            print("INFO: Waiting 3 seconds...")
            
            time.sleep(3)
        return True
    
    def getTargetGroup(self, target_name):
        try:
                return self.elbv2.describe_target_health(
                    TargetGroupArn=target_name,
                )
        except Exception as e:
            raise Exception("Error searching for target group with name [ %s ]. %s" %(target_name, e))
        raise Exception("No target group found with name [ %s ]" %(target_name))

    def waitAutoscalerWithTargetARNHealthy(self, target_name):            

        while True:
            instances = []
            instances_all = self.getTargetGroup(target_name)
            instances_all = instances_all['TargetHealthDescriptions']
            [ instances.append(instance) for instance in instances_all if instance['TargetHealth']['State'] != "draining" ]
            if (self.args.debug=="critical"): print("DEBUG: %s. RETURN: %s" %("instancesTargetGroup",instances))
            instancesReady = 0
            for instance in instances:
                if instance['TargetHealth']['State'] == "healthy":
                    instancesReady+=1

            if len(instances) != instancesReady:
                print("WARNING: TargetGroup in progress: %s to %s" %(instancesReady, len(instances)))
            else:
                print("SUCCESS: Autoscaling ready, desired is %s to %s" %(instancesReady, len(instances) ))
                break

            time.sleep(3)
        return True
    
    def getLoadBalancer(self, elb_name ):
        try:
            return self.elb.describe_instance_health(
                LoadBalancerName=elb_name,
            )
        except Exception as e:
            raise Exception("Error searching for loadbalancer with name [ %s ]. %s" %(elb_name, e))
        raise Exception("No loadbalancer found with name [ %s ]" %(elb_name))

    def waitAutoscalerWithELBHealthy(self, elb_name):
        while True:
            instances = self.getLoadBalancer(elb_name)
            instances = instances['InstanceStates']
            if (self.args.debug=="critical"): print("DEBUG: %s. RETURN: %s" %("instancesELB",instances))
            instancesReady = 0
            for instance in instances:
                if instance['State'] == "InService":
                    instancesReady+=1

            if len(instances) != instancesReady:
                print("WARNING: ELB waiting to all instances all inService: %s to %s" %(instancesReady, len(instances)))
            else:
                print("SUCCESS: ELB ready, desired is %s to %s" %(instancesReady, len(instances) ))
                break

            time.sleep(3)
        return True

    def run(self):
        self.autoscaler = self.getAutoescaler(self.args.name)
        if self.autoscaler is False:
            print("ERROR: Autoscaling not set")
            exit(1)
        
        #Check ASG contains LB or TargetARNs setting
        if len(self.autoscaler['TargetGroupARNs']) > 0:
            self.targetName = self.autoscaler['TargetGroupARNs'][0]
            self.target = "elbv2"
        elif len(self.autoscaler['LoadBalancerNames']) > 0:
            self.targetName  = self.autoscaler['LoadBalancerNames'][0]
            self.target = "elb"
        else:
            print("ERROR: TargetGroupARNs or LoadBalancerNames is not setting, please review.")
            exit(1)


        if not self.targetName or not self.target:
            print("ERROR: TargetGroupARNs or LoadBalancerNames is not setting, please review.")
            exit(1)
        

        if self.setInfoAutoScaler(self.autoscaler):
            self.waitAutoscalerWithNewInstancesHealthy(self.args.name)
            if self.target == "elbv2":
                self.waitAutoscalerWithTargetARNHealthy(self.targetName)
            else:
                self.waitAutoscalerWithELBHealthy(self.targetName)

            OldInfo = dict()
            OldInfo['MaxSize'] = self.max_size
            OldInfo['MinSize'] = self.min_size
            OldInfo['DesiredCapacity'] = self.desired_size

            if self.updateSettingsAutoScaling(self.args.name, OldInfo):
                self.waitAutoscalerWithNewInstancesHealthy(self.args.name)
                print("SUCCESS: All Success.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AutoScaling Services")

    parser.add_argument('--name', help="auto-scaling-group Name")
    parser.add_argument('--region', help="name of region")
    parser.add_argument('--debug', help="show request to aws-cli: [verbose or critical]", default="none",  choices=["verbose", "critical", "none"])

    args = parser.parse_args()
    app = aws_autoscaling_rollout(args)

    app.run()
