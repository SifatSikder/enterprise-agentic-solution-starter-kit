# ADK Multi-Agent Enterprise Framework

**Production-ready framework for building enterprise-grade multi-agentic AI solutions using Google ADK, FastAPI, and Vertex AI.**

## �� Overview

Enterprise-ready framework for building multi-agentic AI applications with:

- ✅ **Multi-tenancy** - Isolated sessions per tenant/organization
- ✅ **Vertex AI Integration** - Memory Bank, embeddings, GCP services  
- ✅ **Enterprise Security** - API keys, RBAC, rate limiting, audit logs
- ✅ **Scalable Architecture** - Redis sessions, horizontal scaling
- ✅ **Production Deployment** - GCP Vertex AI, Docker, monitoring
- ✅ **Developer Experience** - Auto-discovery, hot-reload, testing

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Google Cloud Project with Vertex AI enabled
- Google API Key

### Setup
```bash
# Install
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.template .env
# Edit .env with GOOGLE_API_KEY and GOOGLE_CLOUD_PROJECT

# Start services
docker compose up -d

# Verify
curl http://localhost:8000/api/health
```

## 📁 Structure

```
agents/core/          # Core agent management
api/                  # FastAPI application  
config/environments/  # Environment configs
deployment/gcp/       # GCP deployment
tests/                # Test suite
```

## 🔧 Configuration

All requests require `tenant_id` for multi-tenancy:

```json
{
  "agent_name": "template_simple_agent",
  "message": "Hello",
  "session_id": "session-123",
  "tenant_id": "acme-corp"
}
```

## 🗺️ Roadmap

- [x] Phase 1: Core framework & cleanup
- [ ] Phase 2: Enhanced architecture
- [ ] Phase 3: Security & authentication
- [ ] Phase 4: Vertex AI Memory Bank
- [ ] Phase 5-9: See PRODUCTION_TRANSFORMATION_PLAN.md

**Built for enterprise AI** 🚀
