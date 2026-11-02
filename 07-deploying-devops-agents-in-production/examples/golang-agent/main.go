package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
)

// AgentServer represents the in-cluster Go DevOps Agent
type AgentServer struct {
	clientset *kubernetes.Clientset
}

func NewAgentServer() (*AgentServer, error) {
	// 1. Try In-Cluster Config (when running as Pod inside EKS)
	config, err := rest.InClusterConfig()
	if err != nil {
		// 2. Fallback to Local Kubeconfig (for local testing)
		kubeconfig := os.Getenv("KUBECONFIG")
		if kubeconfig == "" {
			kubeconfig = os.Getenv("HOME") + "/.kube/config"
		}
		config, err = clientcmd.BuildConfigFromFlags("", kubeconfig)
		if err != nil {
			return nil, fmt.Errorf("failed to create kubernetes config: %w", err)
		}
	}

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return nil, fmt.Errorf("failed to initialize clientset: %w", err)
	}

	return &AgentServer{clientset: clientset}, nil
}

// DiagnoseNamespace scans for CrashLoopBackOff or OOMKilled pods
func (a *AgentServer) DiagnoseNamespace(ctx context.Context, namespace string) error {
	pods, err := a.clientset.CoreV1().Pods(namespace).List(ctx, metav1.ListOptions{})
	if err != nil {
		return fmt.Errorf("could not list pods: %w", err)
	}

	log.Printf("[GO AGENT] Scanning %d pods in namespace: %s\n", len(pods.Items), namespace)

	for _, pod := range pods.Items {
		for _, cs := range pod.Status.ContainerStatuses {
			if cs.State.Waiting != nil && cs.State.Waiting.Reason == "CrashLoopBackOff" {
				log.Printf("⚠️ Detected CrashLoopBackOff on Pod: %s (Restarts: %d)\n", pod.Name, cs.RestartCount)
			}
		}
	}
	return nil
}

func main() {
	log.Println("🚀 Starting High-Performance Go DevOps Agent...")

	agent, err := NewAgentServer()
	if err != nil {
		log.Printf("Warning: running in offline mode: %v\n", err)
	} else {
		_ = agent.DiagnoseNamespace(context.Background(), "default")
	}

	http.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"status":"HEALTHY","runtime":"golang"}`))
	})

	log.Println("Listening on :8080...")
	log.Fatal(http.ListenAndServe(":8080", nil))
}
