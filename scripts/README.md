# 🚀 HELIOS GOOGLE CLOUD AUDIT SYSTEM

A comprehensive, automated audit system for Google Cloud projects that provides cost optimization, security analysis, and performance insights.

## 📋 Overview

This audit system consists of several components:

- **Main Audit Runner**: Orchestrates all audit components
- **Individual Audit Scripts**: Specialized scripts for different areas
- **Cleanup Scripts**: Automated resource cleanup with safety checks
- **Comprehensive Reporting**: Detailed analysis and recommendations

## 🏗️ Architecture

```
scripts/
├── audit/                          # Audit scripts
│   ├── gcp_audit_runner.sh        # Main orchestrator
│   ├── api_audit.sh               # API analysis
│   ├── storage_audit.sh           # Storage analysis
│   ├── compute_audit.sh           # Compute resources
│   ├── container_audit.sh         # Container analysis
│   ├── security_audit.sh          # Security & compliance
│   └── cost_analysis.sh           # Cost optimization
├── cleanup/                        # Cleanup scripts
│   ├── storage_cleanup.sh         # Storage cleanup
│   └── api_cleanup.sh             # API cleanup
└── README.md                       # This file
```

## 🚀 Quick Start

### 1. Prerequisites

Install required tools:

```bash
# Install gcloud CLI
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Install jq for JSON processing
# macOS
brew install jq

# Ubuntu/Debian
sudo apt-get install jq

# Install bc for calculations (optional)
# macOS
brew install bc

# Ubuntu/Debian
sudo apt-get install bc
```

### 2. Authentication & Setup

```bash
# Authenticate with Google Cloud
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Verify setup
gcloud config list
```

### 3. Run Complete Audit

```bash
# Make scripts executable
chmod +x scripts/audit/*.sh
chmod +x scripts/cleanup/*.sh

# Run comprehensive audit
bash scripts/audit/gcp_audit_runner.sh
```

## 📊 Audit Components

### 🔌 API Audit (`api_audit.sh`)

**What it analyzes:**
- Enabled APIs and usage patterns
- Essential vs. optional APIs
- Expensive APIs to monitor
- Unused APIs for potential cleanup

**Key findings:**
- Total enabled APIs
- APIs with no usage
- Cost impact categorization
- Safety recommendations

### 🗄️ Storage Audit (`storage_audit.sh`)

**What it analyzes:**
- Cloud Storage buckets and policies
- Compute Engine disks
- Firestore databases
- Cloud SQL instances
- Orphaned resources

**Key findings:**
- Storage usage and costs
- Public access risks
- Lifecycle policy gaps
- Orphaned resource cleanup opportunities

### 💻 Compute Audit (`compute_audit.sh`)

**What it analyzes:**
- Cloud Run services
- Compute Engine instances
- Cloud Functions
- App Engine applications
- Resource scaling and optimization

**Key findings:**
- Running vs. stopped resources
- Resource sizing optimization
- Scaling configuration gaps
- Cost optimization opportunities

### 🐳 Container Audit (`container_audit.sh`)

**What it analyzes:**
- Google Container Registry (GCR)
- Artifact Registry
- Kubernetes clusters
- Container image optimization

**Key findings:**
- Untagged images
- Large image analysis
- Cluster optimization
- Storage cost analysis

### 🔒 Security Audit (`security_audit.sh`)

**What it analyzes:**
- IAM policies and permissions
- Service account security
- Network security (VPC, firewall)
- Secret Manager configuration
- Cloud KMS setup

**Key findings:**
- Public access risks
- High-privilege roles
- Security misconfigurations
- Compliance gaps

### 💰 Cost Analysis (`cost_analysis.sh`)

**What it analyzes:**
- Billing account setup
- Resource costs by service
- Budget configuration
- Cost optimization opportunities

**Key findings:**
- Monthly cost breakdown
- Potential savings
- Budget alert gaps
- Resource optimization recommendations

## 🧹 Cleanup Scripts

### Storage Cleanup (`storage_cleanup.sh`)

**Safe cleanup operations:**
- Orphaned Compute Engine disks
- Old snapshots (configurable retention)
- Untagged container images
- Old Cloud SQL backups

**Safety features:**
- Dry-run mode by default
- User confirmation required
- Configurable retention periods
- Essential resource protection

**Usage:**
```bash
# Preview what would be cleaned up
bash scripts/cleanup/storage_cleanup.sh --dry-run

# Actually perform cleanup
bash scripts/cleanup/storage_cleanup.sh --execute
```

### API Cleanup (`api_cleanup.sh`)

**Safe cleanup operations:**
- Unused APIs (with dependency checks)
- Expensive API review
- Essential API preservation

**Safety features:**
- Never disables essential APIs
- Dependency analysis
- Usage verification
- Dry-run mode by default

**Usage:**
```bash
# Preview what would be disabled
bash scripts/cleanup/api_cleanup.sh --dry-run

# Actually disable APIs
bash scripts/cleanup/api_cleanup.sh --execute
```

## ⚙️ Configuration

### Environment Variables

```bash
# Audit configuration
DRY_RUN=true                    # Enable dry-run mode
CLEANUP_ORPHANED_DISKS=true     # Enable disk cleanup
CLEANUP_OLD_SNAPSHOTS=true      # Enable snapshot cleanup
SNAPSHOT_RETENTION_DAYS=30      # Snapshot retention period
BACKUP_RETENTION_DAYS=90        # Backup retention period

# API cleanup configuration
CLEANUP_UNUSED_APIS=true        # Enable API cleanup
CLEANUP_EXPENSIVE_APIS=false    # Enable expensive API cleanup
```

### Customization

**Essential APIs**: Modify the `ESSENTIAL_APIS` array in `api_cleanup.sh` to include APIs critical to your system.

**Retention Periods**: Adjust retention periods in cleanup scripts based on your business requirements.

**Cleanup Policies**: Enable/disable specific cleanup operations using environment variables.

## 📈 Output & Reports

### Audit Results

Each audit script generates a JSON results file:
- `api_audit_results.json`
- `storage_audit_results.json`
- `compute_audit_results.json`
- `container_audit_results.json`
- `security_audit_results.json`
- `cost_analysis_results.json`

### Comprehensive Report

The main audit runner generates a comprehensive markdown report:
- Executive summary
- Detailed findings by category
- Recommendations and action items
- Cost impact analysis
- Security findings

### Logs

All operations are logged with timestamps:
- `logs/audit/audit_TIMESTAMP.log`
- Detailed execution logs
- Error and warning information

## 🔒 Security Considerations

### Safe by Default

- **Dry-run mode**: All cleanup scripts default to preview mode
- **User confirmation**: Required for destructive operations
- **Essential resource protection**: Critical APIs and resources are never deleted
- **Dependency checking**: Prevents breaking dependent services

### Permission Requirements

**Minimum required roles:**
- `roles/viewer` - Read access to resources
- `roles/compute.viewer` - Compute resource viewing
- `roles/storage.objectViewer` - Storage analysis
- `roles/iam.securityReviewer` - Security analysis

**For cleanup operations:**
- `roles/compute.admin` - Compute resource management
- `roles/storage.admin` - Storage management
- `roles/servicemanagement.admin` - API management

## 🚨 Troubleshooting

### Common Issues

**1. Permission Denied**
```bash
# Check current permissions
gcloud auth list
gcloud config get-value project

# Verify required APIs are enabled
gcloud services list --enabled
```

**2. Missing Dependencies**
```bash
# Install jq
brew install jq  # macOS
sudo apt-get install jq  # Ubuntu

# Install bc
brew install bc  # macOS
sudo apt-get install bc  # Ubuntu
```

**3. API Not Enabled**
```bash
# Enable required APIs
gcloud services enable compute.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable run.googleapis.com
```

### Debug Mode

Enable verbose logging:
```bash
# Set debug environment variable
export DEBUG=true

# Run audit with debug output
bash scripts/audit/gcp_audit_runner.sh
```

## 📅 Recommended Usage

### Audit Frequency

- **Daily**: Cost monitoring and alerts
- **Weekly**: Resource usage review
- **Monthly**: Comprehensive security audit
- **Quarterly**: Full project review

### Cleanup Frequency

- **Weekly**: Storage cleanup (orphaned disks, old snapshots)
- **Monthly**: API cleanup (unused APIs)
- **Quarterly**: Deep cleanup (old backups, untagged images)

## 🤝 Contributing

### Adding New Audit Components

1. Create new audit script in `scripts/audit/`
2. Follow existing script patterns
3. Include JSON output generation
4. Add to main audit runner
5. Update this README

### Customizing for Your Project

1. Modify essential API lists
2. Adjust retention periods
3. Customize resource thresholds
4. Add project-specific checks

## 📚 Resources

### Documentation

- [Google Cloud CLI Documentation](https://cloud.google.com/sdk/docs)
- [Google Cloud Best Practices](https://cloud.google.com/architecture/best-practices)
- [Cost Optimization Guide](https://cloud.google.com/architecture/cost-optimization-on-gcp)

### Related Tools

- [Cloud Custodian](https://cloudcustodian.io/) - Policy-based resource management
- [Terraform](https://www.terraform.io/) - Infrastructure as code
- [Cloud Build](https://cloud.google.com/cloud-build) - Automated deployments

## 📄 License

This audit system is part of the Helios project and follows the same licensing terms.

## 🆘 Support

For issues or questions:

1. Check the troubleshooting section above
2. Review logs for detailed error information
3. Verify prerequisites and permissions
4. Test with dry-run mode first

---

**⚠️ Important**: Always test cleanup operations in a non-production environment first. The audit system is designed to be safe, but resource deletion is irreversible.
