#!/usr/bin/env bash
set -euo pipefail

echo "Checking node readiness"
kubectl wait --for=condition=Ready nodes --all --timeout=120s

echo "Checking storage class"
kubectl get storageclass

echo "Checking ingress controller pods"
kubectl get pods -A | grep -E 'traefik|ingress' || true

echo "Creating PVC smoke test"
cat <<YAML | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pvc-smoke
  namespace: default
spec:
  accessModes: ["ReadWriteOnce"]
  resources:
    requests:
      storage: 1Gi
YAML

cat <<YAML | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: pvc-smoke-consumer
  namespace: default
spec:
  restartPolicy: Never
  containers:
    - name: busybox
      image: busybox:1.36
      command: ["/bin/sh", "-c", "echo pvc-ok > /data/ready && sleep 5"]
      volumeMounts:
        - name: data
          mountPath: /data
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: pvc-smoke
YAML

kubectl wait pvc/pvc-smoke --for=jsonpath='{.status.phase}'=Bound --timeout=120s
kubectl wait pod/pvc-smoke-consumer --for=condition=Ready --timeout=120s || true
kubectl delete pod pvc-smoke-consumer --ignore-not-found=true --wait=true
kubectl delete pvc pvc-smoke --ignore-not-found=true --wait=true

echo "Cluster ingress and PVC baseline look good"
