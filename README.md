# Qwen Serving

Serving Qwen2-1.5B on AWS EKS with a GPU node, streaming tokens back to the client.

## Tech Stack

- **Inference**: Qwen2-1.5B-Instruct, HuggingFace Transformers, PyTorch
- **Serving**: FastAPI, Server-Sent Events (SSE)
- **Infrastructure**: AWS EKS, ECR, Terraform
- **Container**: CUDA 12.1 + Ubuntu 22.04

## Architecture

```
Client → LoadBalancer → EKS Pod (g4dn.xlarge, NVIDIA T4)
                            ├── /ping         (health check)
                            ├── /chat         (streaming response via SSE)
                            └── /chat/sync    (batch response)
```

## Repository Structure

```
qwen_serving/
├── infrastructure/   # Terraform (VPC, EKS, ECR)
├── src/              # Python (main.py, load_model.py, Dockerfile, requirements.txt)
└── k8s/              # Kubernetes manifests (deployment.yaml, service.yaml)
```

## Prerequisites

- AWS CLI configured
- Terraform >= 1.2
- kubectl
- Docker

## Setup

### 1. Infrastructure

```bash
cd infrastructure
terraform init
terraform apply
```

Update kubeconfig after cluster is ready:

```bash
aws eks update-kubeconfig --region us-east-1 --name qwen-serving-eks-cluster
```

### 2. Build and Push Docker Image

```bash
# Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <Account-ID>.dkr.ecr.us-east-1.amazonaws.com

# Build (model is downloaded at build time)
docker build -t qwen-serving src/

# Tag and push
docker tag qwen-serving:latest <Account-ID>.dkr.ecr.us-east-1.amazonaws.com/qwen-serving-ecr-repo:latest
docker push <Account-ID>.dkr.ecr.us-east-1.amazonaws.com/qwen-serving-ecr-repo:latest
```

### 3. Deploy to EKS

```bash
kubectl apply -f k8s/
```

Get the external IP:

```bash
kubectl get svc qwen-service
```

## Usage

Health check:

```bash
curl http://<EXTERNAL-IP>:8080/ping
```

Streaming response:

```bash
curl -X POST http://<EXTERNAL-IP>:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me about Qwen"}' \
  --no-buffer
```

Batch response:

```bash
curl -X POST http://<EXTERNAL-IP>:8080/chat/sync \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me about Qwen"}'
```

## Teardown

Always delete K8s resources before destroying infrastructure to avoid VPC DependencyViolation:

```bash
kubectl delete -f k8s/
cd infrastructure && terraform destroy
```

## Key Design Decisions

- **Model baked into image**: Reproducibility and simplicity for learning purposes. Production alternatives: volume mount or remote model pull at startup.
- **`device_map="auto"`**: Automatically maps model layers to available GPU.
- **`dtype=torch.bfloat16`**: Reduces VRAM usage with minimal accuracy loss.
- **Threading for streaming**: `model.generate()` runs in a separate thread so the main thread can iterate the streamer and yield tokens to the client without blocking.