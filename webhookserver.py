
from flask import Flask, request, jsonify
import os
import json
import yaml
import base64

app=Flask(__name__)

absolute_path = os.path.dirname(__file__) #Get the current folder path
server_private_key=absolute_path+"/Certificates/server.key" # Path to private server key, required for SSL
server_ssl_certificate=absolute_path+"/Certificates/server.crt" #Path to ssl certificate, requred for SSL
allowed_images=("nginx","redis","httpd") #List of allowed images.


def check_file_kubesec(data):      #This function will trigger kubesec hosted at https://v2.kubesec.io/scan and retuns the score"
    
   
    spec=data["request"]["object"]["spec"]
    pod_name=data["request"]["object"]["metadata"]["name"]
    pod_json= {  "apiVersion": "v1",
                  "kind": "Pod",
                  "metadata": {"name": pod_name},
                   "spec": spec
                      
             }
    
    

    yaml_version=yaml.dump(pod_json)   #converting from json to yaml 
    
    
    absolute_path = os.path.dirname(__file__)   
    file_path=absolute_path+"/K8s_file_yaml"  #file name to be created 
    yaml_file=open(file_path, "w") #create the file
    yaml_file.write(yaml_version) #add the yaml data in the created file
    yaml_file.close()

    kubesec_url="curl -sSX POST --data-binary " + "@"+file_path+ " https://v2.kubesec.io/scan" #send the manifest file to kubesec hosted over internet"
    response=os.popen(kubesec_url).read()  #response of kubesec
    converted_response=json.loads(response) #convert the response
    score=converted_response[0]['score']

    return(score)


@app.route('/<index>', methods=['POST'])
def validate_request(index):
     
    json_data=request.json    # to retrieve the JSON data sent by the API server
    json_containers=json_data["request"]["object"]["spec"]["containers"] # to access the conatiners data
    json_uid=json_data["request"]["uid"] # to access the UID of the request
      
    if index=="validate" :       # Validating webhook       
      
      image_allow=True
      for containers in json_containers:
            if containers["image"] not in allowed_images:
               image_allow=False
               break
      
      if image_allow:               # webhook validates the request
         if check_file_kubesec(json_data) >=0 :  #The score is greater than or equal than 0  then the POD will be created
           
            response= {
                     "apiVersion": "admission.k8s.io/v1",
                     "kind": "AdmissionReview",
                        "response": {
                        "uid": json_uid,
                        "allowed": True                
                                          }
                     }
            
         else :
            
            response= {
                  "apiVersion": "admission.k8s.io/v1",
                  "kind": "AdmissionReview",
                     "response": {
                     "uid": json_uid,
                     "allowed": False,    
                        "status": {
                           "code": 403,
                           "message": "SCORE REPORTED BY KUBESEC OF THE MANIFEST FILE BELOW 0"
                                       }
                     }
                  }


         return (response)
      
      else:    # webhook rejected the request
         response= {
                  "apiVersion": "admission.k8s.io/v1",
                  "kind": "AdmissionReview",
                     "response": {
                     "uid": json_uid,
                     "allowed": False,    
                        "status": {
                           "code": 403,
                           "message": "IMAGE(S) NOT IN ALLOWED IMAGES LIST"
                                       }
                     }
                  }
         return (response)
      
    elif index=="mutate":               # Validating webhook 
          

         container_id=0
         serviceaccount={"op": "add", "path": "/spec/serviceAccountName", "value": "sa" }
         satoken={"op": "add", "path": "/spec/automountServiceAccountToken", "value": False}
         add_resources = [serviceaccount,satoken] 
         for containers in json_containers:
            try :            
                   path_resources_cpu_mem="/spec/containers/" + str(container_id)+ "/resources"
                   path_securitycontext="/spec/containers/" + str(container_id)+ "/securityContext"
                   resources_cpu_mem={ "op": "add", "path": path_resources_cpu_mem, "value": {"requests": {"cpu": 0.5 , "memory": "128Mi"}, "limits": {"cpu": 2, "memory": "256Mi"}}}
                   securitycontext = {"op": "add", "path": path_securitycontext, "value": {"allowPrivilegeEscalation": False} } 
                   add_resources.append(resources_cpu_mem)
                   add_resources.append(securitycontext)
                   container_id+=1
                                    
            except(Exception):
   
                return("ERROR")
                  
         bs64_containers_resources=base64.b64encode(json.dumps(add_resources).encode('utf-8'))         
         string_bs64_containers_resources=str(bs64_containers_resources)
         patch_json_b64=string_bs64_containers_resources[2:][:-1]   # I have noticed that Python adds two characters at the beginning  and a character at the end 
                                                                    # of the base64 data, then to extract these characters use [:2][:-1]
                              
         mutation= {
                  "apiVersion": "admission.k8s.io/v1",
                  "kind": "AdmissionReview",
                  "response": {
                     "uid": json_uid,
                     "allowed": True,
                     "patchType": "JSONPatch",
                     "patch": patch_json_b64

                   }
                   }
      
         return(mutation)
           
             


if __name__ == "__main__":
 app.run( host="0.0.0.0", port=5000, threaded=True,ssl_context=(server_ssl_certificate,server_private_key ))
