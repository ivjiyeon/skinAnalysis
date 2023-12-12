import pulumi
import pulumi_gcp as gcp
import pulumi_kubernetes as k8s

# Create a GKE cluster
cluster = gcp.container.Cluster('gke-cluster',
    initial_node_count=3,
    node_version='latest',
    min_master_version='latest',
    node_config=gcp.container.ClusterNodeConfigArgs(
        machine_type='n1-standard-1',
        oauth_scopes=[
            'https://www.googleapis.com/auth/compute',
            'https://www.googleapis.com/auth/devstorage.read_only',
            'https://www.googleapis.com/auth/logging.write',
            'https://www.googleapis.com/auth/monitoring'
        ],
    ),
)

# Export the Kubeconfig
kubeconfig = pulumi.Output.all(cluster.name, cluster.endpoint, cluster.master_auth).apply(
    lambda args: """apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: {2}
    server: https://{1}
  name: {0}
contexts:
- context:
    cluster: {0}
    user: {0}
  name: {0}
current-context: {0}
kind: Config
preferences: {{}}
users:
- name: {0}
  user:
    auth-provider:
       name: gcp
""".format(args[0], args[1], args[2]['cluster_ca_certificate']))

k8s_provider = k8s.Provider('gke_k8s', kubeconfig=kubeconfig)

# Define the Kubernetes Deployment for FastAPI application
app_labels = {"app": "fastapi"}
app_deployment = k8s.apps.v1.Deployment('fastapi-app',
    metadata=k8s.meta.v1.ObjectMetaArgs(
        labels=app_labels
    ),
    spec=k8s.apps.v1.DeploymentSpecArgs(
        replicas=1,
        selector=k8s.meta.v1.LabelSelectorArgs(match_labels=app_labels),
        template=k8s.core.v1.PodTemplateSpecArgs(
            metadata=k8s.meta.v1.ObjectMetaArgs(labels=app_labels),
            spec=k8s.core.v1.PodSpecArgs(
                containers=[k8s.core.v1.ContainerArgs(
                    name='fastapi',
                    image='DOCKER_IMAGE_URL',  # Replace with your Docker image URL
                    ports=[k8s.core.v1.ContainerPortArgs(container_port=80)],
                )],
            ),
        ),
    ), opts=pulumi.ResourceOptions(provider=k8s_provider)
)

# Export the cluster name and kubeconfig
pulumi.export('cluster_name', cluster.name)
pulumi.export('kubeconfig', kubeconfig)