# Enterprise Production Incident Scenarios & Root Cause Analysis (6+ Years Experience)

These real-world post-mortem scenarios evaluate your ability to lead high-stakes troubleshooting during production emergencies and architectural failures.

---

### Incident 1: Connection Pool Starvation & Database Thundering Herd during Canary Release
**The Crisis**: During a major release of the payment-gateway service, Argo Rollouts shifted 20% of traffic to the new canary version. Within 90 seconds, the primary Aurora PostgreSQL database CPU spiked to 100%, and all application pods (both canary and stable) began throwing `FATAL: remaining connection slots are reserved for non-replication superuser connections`.

**Triage & Lead Response**:
1. **Immediate Stabilization**:
   - Immediately abort the Canary rollout via Argo Rollouts CLI: `kubectl argo rollouts abort payment-gateway -n payment-prod`.
   - Scale down canary pods to 0 to release hung database connections.
2. **Root Cause Analysis (RCA)**:
   - Comparing database metrics between old and new pods revealed the root cause:
     - The old version used an internal HikariCP connection pool with `maxPoolSize: 10`.
     - A developer updated the configuration in the new version with `maxPoolSize: 50`.
     - When the canary pods spun up alongside the existing pods, the total connection requests exceeded Postgres's `max_connections` limit.
   - Compounding factor: Pods were connecting directly to PostgreSQL instead of through a pooled proxy.
3. **Permanent Architectural Remediation**:
   - Introduce **AWS RDS Proxy** or **PgBouncer** between the Kubernetes pods and the database cluster.
   - Enforce database connection limits per service in Kubernetes configuration schemas.
   - Add automated AnalysisTemplate rules in Argo Rollouts that watch `database_active_connections` in addition to HTTP 5xx errors.

---

### Incident 2: Supply Chain Zero-Day (Malicious Transitive NPM Dependency)
**The Crisis**: At 2:00 AM, an automated security bulletin announces that a widely-used transitive npm package has been hijacked and publishes version `3.4.1` containing an obfuscated crypto-miner and reverse shell. Your organization runs 80 Node.js microservices.

**Triage & Lead Response**:
1. **Immediate Blast Radius Assessment**:
   - Query your central **Dependency-Track** or **Snyk / Trivy SBOM inventory**: Identify exactly which microservice container images in Amazon ECR contain the vulnerable package version.
2. **Immediate Pipeline Freeze & Admission Blocking**:
   - Apply a cluster-wide **Kyverno / OPA Gatekeeper policy** to block deployment of any container image with the vulnerable package digest:
     ```yaml
     apiVersion: kyverno.io/v1
     kind: ClusterPolicy
     metadata:
       name: block-compromised-cve
     spec:
       validationFailureAction: Enforce
       rules:
         - name: block-bad-package
           match:
             resources:
               kinds: [Pod]
           validate:
             message: "Deployment blocked: Image contains compromised package CVE-2026-XXXX."
     ```
3. **Automated Mass Remediation**:
   - Run an automated script across all 80 GitHub repositories to pin the dependency to the known safe version in `package-lock.json` via Renovate / Dependabot bot PRs.
   - Dispatch GitHub Actions reusable workflows to compile, scan, and promote clean images through ArgoCD GitOps pipelines.

---

### Incident 3: CoreDNS Exhaustion & In-Cluster DNS Lookup Timeouts
**The Crisis**: After migrating 50 services into an EKS cluster, applications sporadically encounter 5-second connection delays (`dial tcp: i/o timeout`). Latency spikes across all microservices, but CPU and memory usage across nodes remain under 30%.

**Triage & Lead Response**:
1. **Root Cause Analysis (DNS Conntrack & ndots:5 Issue)**:
   - Linux `/etc/resolv.conf` in Kubernetes defaults to `ndots:5`.
   - For every external DNS query (e.g. `api.stripe.com`), the pod issues 4 sequential internal DNS queries (`api.stripe.com.default.svc.cluster.local`, `api.stripe.com.svc.cluster.local`, etc.) before querying the public domain.
   - 50 microservices making high-frequency external API calls generated tens of thousands of DNS requests per second, overwhelming CoreDNS pods and triggering Linux kernel `nf_conntrack` UDP packet drop.
2. **Remediation & Performance Hardening**:
   - Deploy **NodeLocal DNSCache** DaemonSet: Runs a DNS caching agent on every single Kubernetes worker node, eliminating cross-node CoreDNS network hops and UDP conntrack saturation.
   - Update application deployment manifests: Set `dnsConfig.options: ndots: 2` or append a trailing dot (`api.stripe.com.`) to external endpoints in code to bypass internal domain searches completely.
   - Autoscale CoreDNS horizontally using the `cluster-proportional-autoscaler`.
