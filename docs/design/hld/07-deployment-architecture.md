# Vortex Deployment Architecture

**Version:** 1.0  
**Date:** 2025-01-08  
**Related:** [System Overview](01-system-overview.md) | [Security Design](06-security-design.md)

## 1. Deployment Overview

Vortex supports multiple deployment scenarios from individual development workstations to enterprise-scale container orchestration platforms. The deployment architecture emphasizes simplicity, security, and operational reliability.

### 1.1 Deployment Scenarios
```mermaid
graph TB
    subgraph "Development"
        Dev[Local Development]
        IDE[IDE Integration]
        Testing[Local Testing]
    end
    
    subgraph "Production"
        Container[Docker Container]
        K8s[Kubernetes]
        Cloud[Cloud Functions]
    end
    
    subgraph "Enterprise"
        OnPrem[On-Premises]
        Hybrid[Hybrid Cloud]
        MultiCloud[Multi-Cloud]
    end
    
    Dev --> Container
    Container --> K8s
    Container --> Cloud
    K8s --> OnPrem
    K8s --> Hybrid
    Cloud --> MultiCloud
    
    style Container fill:#e1f5fe
    style K8s fill:#e1f5fe
```

### 1.2 Deployment Characteristics
| Aspect | Local Dev | Container | Kubernetes | Cloud Function |
|--------|-----------|-----------|------------|----------------|
| **Complexity** | Low | Medium | High | Medium |
| **Scalability** | Single user | Multi-instance | Auto-scaling | Serverless |
| **Resource Control** | Full | Isolated | Orchestrated | Managed |
| **Cost** | Development only | Infrastructure | Platform + Ops | Usage-based |
| **Use Case** | Development, Testing | Production, CI/CD | Enterprise, Scale | Event-driven |

## 2. Container Architecture

### 2.1 Docker Container Design
```dockerfile
# Multi-stage build for production efficiency
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create application user
RUN useradd --create-home --shell /bin/bash vortex

# Set up Python environment
COPY pyproject.toml /tmp/
RUN pip install --user --no-cache-dir -e /tmp/

# Production stage
FROM python:3.11-slim

# Copy Python packages from builder
COPY --from=builder /home/vortex/.local /home/vortex/.local

# Create application user in production image
RUN useradd --create-home --shell /bin/bash vortex

# Set up application directory
WORKDIR /app
COPY --chown=vortex:vortex src/vortex ./vortex/
COPY --chown=vortex:vortex docker/ ./

# Create data directory with proper permissions
RUN mkdir -p /data && chown vortex:vortex /data

# Switch to non-root user
USER vortex

# Set Python path
ENV PATH=/home/vortex/.local/bin:$PATH
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import vortex; print('OK')" || exit 1

# Default command
CMD ["./entrypoint.sh"]
```

### 2.2 Container Configuration
```yaml
# docker-compose.yml for development
version: '3.8'

services:
  vortex:
    build: .
    environment:
      - VORTEX_OUTPUT_DIR=/data
      - VORTEX_LOGGING_LEVEL=INFO
      - VORTEX_DRY_RUN=false
    env_file:
      - .env.local
    volumes:
      - ./data:/data
      - ./config:/app/config:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import vortex; print('OK')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### 2.3 Container Security
```mermaid
graph TB
    subgraph "Container Security Layers"
        User[Non-root User]
        FS[Read-only Filesystem]
        Caps[Dropped Capabilities]
        Secrets[External Secrets]
    end
    
    subgraph "Runtime Security"
        Scanner[Image Scanning]
        Monitor[Runtime Monitoring]
        Policy[Security Policies]
    end
    
    subgraph "Network Security"
        Firewall[Network Policies]
        TLS[TLS Encryption]
        Proxy[Egress Proxy]
    end
    
    User --> Scanner
    FS --> Monitor
    Caps --> Policy
    Secrets --> Firewall
    
    style User fill:#c8e6c9
    style Secrets fill:#fff3e0
```

**Security Implementation:**
```dockerfile
# Security hardening
USER vortex:vortex
COPY --chown=vortex:vortex . .

# Read-only root filesystem
VOLUME ["/tmp", "/data"]

# Drop all capabilities
--cap-drop=ALL

# No new privileges
--security-opt=no-new-privileges:true

# AppArmor/SELinux profiles
--security-opt=apparmor:vortex-profile
```

## 3. Kubernetes Deployment

### 3.1 Kubernetes Resources
```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: vortex
  labels:
    app.kubernetes.io/name: vortex
    app.kubernetes.io/version: "1.0"

---
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: vortex-config
  namespace: vortex
data:
  config.json: |
    {
      "futures": {
        "GOLD": {"code": "GC", "cycle": "GJMQVZ"}
      }
    }
  VORTEX_OUTPUT_DIR: "/data"
  VORTEX_LOGGING_LEVEL: "INFO"
  VORTEX_BACKUP_DATA: "true"

---
# secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: vortex-secrets
  namespace: vortex
type: Opaque
data:
  VORTEX_USERNAME: <base64-encoded-username>
  VORTEX_PASSWORD: <base64-encoded-password>

---
# pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: vortex-data
  namespace: vortex
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 100Gi
  storageClassName: fast-ssd
```

### 3.2 CronJob Deployment
```yaml
# cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: vortex-daily
  namespace: vortex
spec:
  schedule: "0 6 * * 1-5"  # 6 AM weekdays
  timeZone: "America/New_York"
  concurrencyPolicy: Forbid
  failedJobsHistoryLimit: 3
  successfulJobsHistoryLimit: 3
  jobTemplate:
    spec:
      template:
        metadata:
          labels:
            app.kubernetes.io/name: vortex
            app.kubernetes.io/component: data-download
        spec:
          restartPolicy: OnFailure
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            runAsGroup: 1000
            fsGroup: 1000
          containers:
          - name: vortex
            image: vortex:1.0
            imagePullPolicy: IfNotPresent
            env:
            - name: VORTEX_OUTPUT_DIR
              value: "/data"
            envFrom:
            - configMapRef:
                name: vortex-config
            - secretRef:
                name: vortex-secrets
            resources:
              requests:
                memory: "512Mi"
                cpu: "250m"
              limits:
                memory: "1Gi"
                cpu: "500m"
            volumeMounts:
            - name: data
              mountPath: /data
            - name: config
              mountPath: /app/config
              readOnly: true
          volumes:
          - name: data
            persistentVolumeClaim:
              claimName: vortex-data
          - name: config
            configMap:
              name: vortex-config
```

### 3.3 Monitoring and Observability
```yaml
# servicemonitor.yaml (Prometheus)
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: vortex-metrics
  namespace: vortex
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: vortex
  endpoints:
  - port: metrics
    interval: 30s
    path: /metrics

---
# networkpolicy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: vortex-netpol
  namespace: vortex
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: vortex
  policyTypes:
  - Ingress
  - Egress
  egress:
  - to: []  # Allow all egress for data provider APIs
    ports:
    - protocol: TCP
      port: 443
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: UDP
      port: 53  # DNS
```

## 4. Cloud-Native Deployments

### 4.1 AWS Deployment
```yaml
# CloudFormation template excerpt
Resources:
  VortexTaskDefinition:
    Type: AWS::ECS::TaskDefinition
    Properties:
      Family: vortex
      NetworkMode: awsvpc
      RequiresCompatibilities:
        - FARGATE
      Cpu: 512
      Memory: 1024
      ExecutionRoleArn: !Ref VortexExecutionRole
      TaskRoleArn: !Ref VortexTaskRole
      ContainerDefinitions:
        - Name: vortex
          Image: !Sub "${AWS::AccountId}.dkr.ecr.${AWS::Region}.amazonaws.com/vortex:latest"
          Environment:
            - Name: VORTEX_OUTPUT_DIR
              Value: /data
          Secrets:
            - Name: VORTEX_USERNAME
              ValueFrom: !Ref VortexUserSecret
            - Name: VORTEX_PASSWORD
              ValueFrom: !Ref VortexPasswordSecret
          MountPoints:
            - SourceVolume: data
              ContainerPath: /data
          LogConfiguration:
            LogDriver: awslogs
            Options:
              awslogs-group: !Ref VortexLogGroup
              awslogs-region: !Ref AWS::Region
              awslogs-stream-prefix: vortex
      Volumes:
        - Name: data
          EFSVolumeConfiguration:
            FileSystemId: !Ref VortexEFS
            
  VortexScheduledTask:
    Type: AWS::Events::Rule
    Properties:
      ScheduleExpression: "cron(0 6 ? * MON-FRI *)"
      State: ENABLED
      Targets:
        - Arn: !GetAtt VortexCluster.Arn
          Id: VortexTarget
          RoleArn: !GetAtt VortexEventRole.Arn
          EcsParameters:
            TaskDefinitionArn: !Ref VortexTaskDefinition
            LaunchType: FARGATE
            NetworkConfiguration:
              AwsVpcConfiguration:
                SecurityGroups:
                  - !Ref VortexSecurityGroup
                Subnets:
                  - !Ref PrivateSubnet1
                  - !Ref PrivateSubnet2
```

### 4.2 Google Cloud Deployment
```yaml
# Cloud Run service
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: vortex
  namespace: default
  annotations:
    run.googleapis.com/cpu-throttling: "false"
    run.googleapis.com/execution-environment: gen2
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/maxScale: "1"
        run.googleapis.com/execution-environment: gen2
    spec:
      containerConcurrency: 1
      timeoutSeconds: 3600
      containers:
      - image: gcr.io/project-id/vortex:latest
        resources:
          limits:
            cpu: "1"
            memory: "2Gi"
        env:
        - name: VORTEX_OUTPUT_DIR
          value: "/data"
        - name: VORTEX_USERNAME
          valueFrom:
            secretKeyRef:
              name: vortex-secrets
              key: username
        - name: VORTEX_PASSWORD
          valueFrom:
            secretKeyRef:
              name: vortex-secrets
              key: password
        volumeMounts:
        - name: data
          mountPath: /data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: vortex-data
```

### 4.3 Azure Deployment
```yaml
# Azure Container Instances
apiVersion: 2019-12-01
location: eastus
name: vortex-container-group
properties:
  containers:
  - name: vortex
    properties:
      image: vortex.azurecr.io/vortex:latest
      resources:
        requests:
          cpu: 0.5
          memoryInGb: 1
      environmentVariables:
      - name: VORTEX_OUTPUT_DIR
        value: /data
      - name: VORTEX_USERNAME
        secureValue: <from-key-vault>
      - name: VORTEX_PASSWORD
        secureValue: <from-key-vault>
      volumeMounts:
      - name: data-volume
        mountPath: /data
  osType: Linux
  restartPolicy: Never
  volumes:
  - name: data-volume
    azureFile:
      shareName: vortex-data
      storageAccountName: vortexstorage
      storageAccountKey: <storage-key>
```

## 5. Infrastructure Requirements

### 5.1 Resource Specifications
| Component | CPU | Memory | Storage | Network |
|-----------|-----|--------|---------|---------|
| **Development** | 0.5 cores | 512MB | 10GB | Broadband |
| **Production Single** | 1 core | 1GB | 100GB | 100Mbps |
| **Production Scaled** | 2-4 cores | 2-4GB | 500GB+ | 1Gbps |
| **Enterprise** | 4+ cores | 8GB+ | 1TB+ | 10Gbps |

### 5.2 Storage Requirements
```mermaid
graph TB
    subgraph "Storage Layers"
        App[Application Data]
        Config[Configuration]
        Logs[Log Files]
        Cache[Temporary Cache]
        Backup[Backup Storage]
    end
    
    subgraph "Storage Types"
        Fast[Fast SSD - Application]
        Standard[Standard - Logs/Config]
        Archive[Archive - Backup]
    end
    
    App --> Fast
    Config --> Standard
    Logs --> Standard
    Cache --> Fast
    Backup --> Archive
    
    style Fast fill:#c8e6c9
    style Archive fill:#fff3e0
```

**Storage Allocation:**
- **Application Data:** 80% of total storage (CSV/Parquet files)
- **Configuration:** 1% (JSON configs, instrument definitions)
- **Logs:** 10% (operational logs with rotation)
- **Temporary Cache:** 5% (download buffers, processing temp)
- **Backup Reserve:** 4% (metadata, recovery data)

### 5.3 Network Architecture
```mermaid
graph TB
    subgraph "External Networks"
        Internet[Internet]
        Providers[Data Providers]
    end
    
    subgraph "DMZ"
        LB[Load Balancer]
        Proxy[Egress Proxy]
    end
    
    subgraph "Private Network"
        App[Vortex Pods]
        Storage[Storage Systems]
        Monitor[Monitoring]
    end
    
    Internet --> LB
    LB --> App
    App --> Proxy
    Proxy --> Providers
    App --> Storage
    App --> Monitor
    
    style App fill:#e1f5fe
    style Proxy fill:#fff3e0
```

**Network Requirements:**
- **Ingress:** Health checks, monitoring endpoints
- **Egress:** HTTPS to data provider APIs
- **Internal:** Pod-to-pod communication, storage access
- **Security:** Network policies, TLS encryption

## 6. Operational Procedures

### 6.1 Deployment Pipeline
```mermaid
graph LR
    subgraph "CI/CD Pipeline"
        Code[Code Commit]
        Build[Build & Test]
        Scan[Security Scan]
        Push[Push Image]
        Deploy[Deploy]
    end
    
    subgraph "Environments"
        Dev[Development]
        Staging[Staging]
        Prod[Production]
    end
    
    Code --> Build
    Build --> Scan
    Scan --> Push
    Push --> Dev
    Dev --> Staging
    Staging --> Prod
    
    style Build fill:#e1f5fe
    style Scan fill:#fff3e0
    style Prod fill:#c8e6c9
```

**Pipeline Stages:**
1. **Build & Test:** Unit tests, integration tests, linting
2. **Security Scan:** Container image vulnerability scanning
3. **Push Image:** Tag and push to registry
4. **Deploy Development:** Automated deployment to dev environment
5. **Deploy Staging:** Manual approval for staging deployment
6. **Deploy Production:** Manual approval with rollback capability

### 6.2 Health Checks and Monitoring
```python
# Health check endpoint
@app.route('/health')
def health_check():
    checks = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'checks': {
            'filesystem': check_filesystem_access(),
            'providers': check_provider_connectivity(),
            'configuration': check_configuration_validity(),
            'dependencies': check_dependency_versions()
        }
    }
    
    if all(checks['checks'].values()):
        return jsonify(checks), 200
    else:
        return jsonify(checks), 503

# Readiness check
@app.route('/ready')
def readiness_check():
    # Check if application is ready to accept traffic
    return jsonify({'status': 'ready'}), 200

# Liveness check  
@app.route('/live')
def liveness_check():
    # Check if application is alive (not deadlocked)
    return jsonify({'status': 'alive'}), 200
```

### 6.3 Backup and Recovery
```bash
#!/bin/bash
# Backup script for Vortex data

BACKUP_DIR="/backup/vortex"
DATA_DIR="/data"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR/$DATE"

# Backup data files
tar -czf "$BACKUP_DIR/$DATE/data.tar.gz" \
    --exclude="*.tmp" \
    --exclude="*.log" \
    "$DATA_DIR"

# Backup configuration
kubectl get configmap vortex-config -o yaml > "$BACKUP_DIR/$DATE/config.yaml"

# Upload to cloud storage
aws s3 cp "$BACKUP_DIR/$DATE/" s3://vortex-backups/$DATE/ --recursive

# Retention policy (keep 30 days)
find "$BACKUP_DIR" -type d -mtime +30 -exec rm -rf {} \;
```

## 7. Security Considerations

### 7.1 Runtime Security
```yaml
# Pod Security Standards
apiVersion: v1
kind: Pod
metadata:
  name: vortex
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: vortex
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
```

### 7.2 Secret Management
```yaml
# External Secrets Operator
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: vault-backend
spec:
  provider:
    vault:
      server: "https://vault.company.com"
      path: "secret"
      version: "v2"
      auth:
        kubernetes:
          mountPath: "kubernetes"
          role: "vortex"

---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: vortex-credentials
spec:
  refreshInterval: 15s
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: vortex-secrets
    creationPolicy: Owner
  data:
  - secretKey: VORTEX_USERNAME
    remoteRef:
      key: vortex/credentials
      property: username
  - secretKey: VORTEX_PASSWORD
    remoteRef:
      key: vortex/credentials
      property: password
```

## 8. Disaster Recovery

### 8.1 Recovery Procedures
```mermaid
graph TB
    Disaster[Disaster Event] --> Assess{Assess Impact}
    
    Assess -->|Data Loss| DataRecover[Data Recovery]
    Assess -->|Service Down| ServiceRecover[Service Recovery]
    Assess -->|Infrastructure| InfraRecover[Infrastructure Recovery]
    
    DataRecover --> Restore[Restore from Backup]
    ServiceRecover --> Redeploy[Redeploy Application]
    InfraRecover --> Rebuild[Rebuild Infrastructure]
    
    Restore --> Validate[Validate Data Integrity]
    Redeploy --> Test[Test Service Health]
    Rebuild --> Configure[Reconfigure Services]
    
    Validate --> Resume[Resume Operations]
    Test --> Resume
    Configure --> Resume
    
    style Disaster fill:#ffcdd2
    style Resume fill:#c8e6c9
```

### 8.2 Recovery Time Objectives
| Scenario | RTO | RPO | Procedure |
|----------|-----|-----|-----------|
| **Application Crash** | 5 minutes | 0 | Container restart |
| **Data Corruption** | 1 hour | 1 day | Restore from backup |
| **Infrastructure Failure** | 4 hours | 1 day | Rebuild and restore |
| **Region Outage** | 8 hours | 1 day | Failover to secondary region |

### 8.3 Business Continuity
- **Multi-Region Deployment:** Active-passive configuration
- **Data Replication:** Cross-region backup storage
- **Provider Failover:** Multiple data source redundancy
- **Documentation:** Runbooks for common failure scenarios

## Related Documents

- **[System Overview](01-system-overview.md)** - Overall system architecture
- **[Security Design](06-security-design.md)** - Security implementation details
- **[Integration Design](08-integration-design.md)** - External system interfaces
- **[Product Requirements](../../requirements/prd/product-requirements.md)** - Business requirements

---

**Next Review:** 2025-02-08  
**Reviewers:** DevOps Lead, Security Architect, Infrastructure Team