# AWS Autoscaling Rollout

## Introducion:
aws-autoscaling-rollout permite la sustitución de alta disponibilidad/sin tiempo de inactividad, de todas las instancias EC2 en un grupo de escalamiento automático (que se puede conectar a un ELB). 
Hace esto de manera "rodante", escala la misma cantidad de equipos que estan funcionando y luego desescala. 
Esta secuencia de comandos admite AMBOS Balanceadores de carga de aplicaciones (ALB) y los Balanceadores de carga "clásicos" (CLB) de Amazon, pero ** NO es compatible actualmente con ECS **.

## Uso potencial:
Algunos usos potenciales para aws-autoscaling-rollout se enumeran a continuación:

1. Deploy de un nuevo código de aplicación. La utilización de este script provocará la finalización de las instancias de EC2 con el fin de lanzar un nuevo código de alta disponibilidad sin incurrir en tiempo de inactividad.
2. Rotar y/o actualizar sus instancias a un estado new/vainilla, todas las instancias anteriores de EC2 pueden ser reemplazadas por instancias EC2 más nuevas. Esto puede ayudar a restablecer las instancias en el caso de que los registros o los archivos temporales hayan rellenado su instancia, o su aplicación haya consumido todos los recursos de RAM/Disco disponibles.

## Requerimientos:
Python 3
 ``` pip install -r requeriments.txt ```

## Instrucciones de uso:
export AWS_ACCESS_KEY_ID="${AWS_KEY_ID}" ; export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_KEY}" ; ~/aws-autoscaling-rollout.py --name=${AutoScalingGroupName} --region=${Region}

## Opciones de script:
### --name
  Especificar nombre de ASG
### --region
  Especificar region de AWS