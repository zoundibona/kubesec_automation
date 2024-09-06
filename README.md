# KUBESEC

Kubesec is a tool that is used to scan your kubernetes manifests file in order to detect security issues.
There are severals ways to run kubesec.
It can be installed locally or use the remote kubesec available at https://v2.kubesec.io/scan
For the local installations, you have the option of 

* binary
* docker image

# SCAN FILE WITH KUBESEC

Let us assume that your manifest K8s.yaml is as below :

    apiVersion: v1
    kind: Pod
    metadata:
      name: pod
    spec:
      containers:
      - image: nginx
        imagePullPolicy: Always
        name: pod
        resources: {}
        securityContext:
          privileged: true
      serviceAccount: default
      serviceAccountName: default
      




To scan the manifest file, you can will run the below command :   <br>
        **kubesec scan K8s.yaml**  <br>

This will return below output

      [
        {
          "object": "Pod/pod.default",
          "valid": true,
          "fileName": "API",
          "message": "Failed with a score of -27 points",
          "score": -27,
          "scoring": {
            "critical": [
              {
                "id": "Privileged",
                "selector": "containers[] .securityContext .privileged == true",
                "reason": "Privileged containers can allow almost completely unrestricted host access",
                "points": -30
              }
            ],
            "passed": [
              {
                "id": "ServiceAccountName",
                "selector": ".spec .serviceAccountName",
                "reason": "Service accounts restrict Kubernetes API access and should be configured with least privilege",
                "points": 3
              }
            ],
            "advise": [
              {
                "id": "ApparmorAny",
                "selector": ".metadata .annotations .\"container.apparmor.security.beta.kubernetes.io/nginx\"",
                "reason": "Well defined AppArmor policies may provide greater protection from unknown threats. WARNING: NOT PRODUCTION READY",
                "points": 3
              },
        ******TRUNCATED *******
    

The output returns a field called score, if the score is greater or equal than 0 then the file has passed the test, otherwise it has failed due to securities configurations
<br>
For example configuration like securityContext: Privileged: True will likely make the score to be below 0 like in this case.


# LIMITATION OF USING KUBESEC VIA CLI

Up to now, we can see kubesec has to be runned manually before deploying to Kubernetes cluster. 
What if the Kube API server in charge of creating the POD was able to trigger an external application that would check the score of the manifest file ? 
If the returned score is below 0 the POD is creation is rejected, otherwise it allows the POD to be created.


# WEBHOOK AND KUBESEC
To solve the problem mentionned earlier, it is possisble to use a Webhook that will trigger the external application before creating or rejected the POD.
I have already written an article of Kubernetes Webhook, kindly refer to this article  https://github.com/zoundibona/K8sWebhook

The script is written in Python Flask. <br>
In this case I have used kubesec available at https://v2.kubesec.io/scan <br>
the below command will send the request to kubesec to check the manifest file <br>

     curl -sSX POST --data-binary  @k8filename  https://v2.kubesec.io/scan 

# DEMO

Let us below manifest file

        apiVersion: v1
        kind: Pod
        metadata:
          creationTimestamp: null
          labels:
            run: pod
          name: pod
        spec:
          containers:
          - image: nginx
            name: pod
            resources: {}
            securityContext:
              privileged: true
          dnsPolicy: ClusterFirst
          restartPolicy: Always
        status: {}

As you can privileged is set to true,
Let us try to create the manifest file <br>

**$ kubectl apply -f testpod.yaml** <br>

Output returned 

    Error from server: error when creating "testpod.yaml": admission webhook "validate-webhook.test.com" denied the request: SCORE REPORTED BY KUBESEC OF THE MANIFEST FILE BELOW 0

We can see that the Webhook returned a message to API server that containing **"SCORE REPORTED BY KUBESEC OF THE MANIFEST FILE BELOW 0"**, this is because of securityContext configuration. <br>

Now let us modify the manifest file by changing **privileged value to false**

        apiVersion: v1
        kind: Pod
        metadata:
          creationTimestamp: null
          labels:
            run: pod
          name: pod
        spec:
          containers:
          - image: nginx
            name: pod
            resources: {}
            securityContext:
              privileged: false
          dnsPolicy: ClusterFirst
          restartPolicy: Always
        status: {}


Let us apply the modified manifest file

$ **kubectl apply -f testpod.yaml**  <br>
$ **kubectl get pods**  <br>

    NAME   READY   STATUS    RESTARTS   AGE
    pod    1/1     Running   0          6s




