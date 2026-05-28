### SERVIDOR

**Hardware:**

- CPU: Intel Core i7-6700 (Skylake)
- Placa-mãe: POS-PIB150DT (Versão 0409.X)
- RAM: 32GB DDR4-2666 (Operando a 1333 MHz)
- iGPU: Intel HD Graphics 530
- dGPU: NVIDIA GeForce GTX 1060 6GB GDDR5 (GP106-400 Rev A1) - **Arquitetura Pascal (Compute Capability 6.1)**
- Armazenamento: SSD WD Green SATA 2.5 1TB
- Rede: Realtek PCIe GbE (1Gbps)

**Software (Host):**

- SO: Windows Server 2025 Datacenter (Versão 24H2, Build 1000.26100.275.0)
- Rede: Grupo de Trabalho (Sem Active Directory). Regras de NAT/Port Forwarding já estabelecidas e funcionais.
- Driver NVIDIA: 576.57 (WDDM Mode)
- CUDA Toolkit (Host): 12.9.86

**Software (Guest / WSL2):**

- WSL: Versão 2.6.3.0 (Kernel 6.6.87.2-1, WSLg 1.0.71)
- Distro: **Ubuntu 26.04 LTS** (Instalação Limpa, Nome da Instância: `Ubuntu-26.04`)
- Driver NVIDIA (Guest): 575.57.05 (Passthrough funcional, Xwayland ativo com workaround de teclado ABNT2 via XKB)
- Stack de Execução: **100% Dockerizada** (NVIDIA Container Toolkit)

**Stack RAG Alvo (Docker):**

- Banco de Dados: PostgreSQL com `pgvector` (`vitalia_db`)
- Cache: Redis (`vitalia_redis`)
- Inferência/Embeddings: Ollama (`vitalia_ollama` rodando `llama3.2:3b` e `nomic-embed-text`)

---
