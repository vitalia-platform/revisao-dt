# Revisão Integrativa — Sistema de IA para Pesquisa Científica

> **Repositório Template.** Este é o ponto de partida para qualquer nova Revisão Integrativa da Literatura assistida por IA. Clone este repositório, configure seu ambiente e invoque `/integrative-review` para começar.

---

## 🏗️ Arquitetura do Sistema

Este sistema opera em duas camadas separadas:

```
revisao-integrativa/          ← ESTE REPOSITÓRIO (template base — não altere no GitHub)
├── kit/                      ← Kit de Agentes (submodule: vitalia-agent-kit)
│   └── [agents, skills, workflows, scripts]
├── .agent/                   ← Sistema de Configuração Local
│   └── session/              ← Contexto de sessão da IA (seu repo privado, ver Passo 3)
│       ├── CONTEXT.md        ← Estado atual da revisão
│       └── SESSION_HISTORY.md
└── inicio/                   ← Templates e documentação de referência
    ├── 00_SUMARIO_EXECUTIVO.md
    ├── TEMPLATE_FICHAMENTO.md
    ├── TEMPLATE_PRISMA_LOG.csv
    └── criteria_config.template.yaml

seu-repo-de-trabalho/         ← CRIADO POR VOCÊ (ver seção "Criando seu repositório")
├── [pasta-exportacao]/       ← Nome definido no painel /integrative-review
├── [pasta-amostra]/          ← Nome definido no painel /integrative-review
├── [pasta-lotes]/            ← Nome definido no painel /integrative-review
├── [pasta-saida]/            ← Nome definido no painel /integrative-review
├── [pasta-fichamentos]/      ← Nome definido no painel /integrative-review
└── criteria_config.yaml      ← Gerado pelo /integrative-review (cérebro do sistema)
```

| Componente | Para que serve |
|---|---|
| 🛠️ **Kit de Agentes** (`kit/`) | Agentes, skills, regras e workflows. Submodule compartilhado entre projetos. |
| 🧠 **Contexto de Sessão** (`.agent/session/`) | Memória persistente da IA entre máquinas. Seu repositório privado. |
| 📚 **Dados da Revisão** (pastas de trabalho) | CSVs, PDFs, fichamentos e saída PRISMA. Ficam no seu repo de trabalho. |

---

## 1. Pré-requisitos

- **Git** 2.28+ com suporte a submodules
- **Python** 3.10+
- **Chave SSH** configurada no GitHub
- **Antigravity** (IDE / Gemini CLI) configurada para utilizar os agentes do kit
- **Servidor Local (opcional, recomendado):** Stack Docker com Ollama para processamento de lotes massivos (ver `Hardware.md`)

### Gerando sua chave SSH (se ainda não tiver)

```bash
ssh-keygen -t ed25519 -C "seu-email@instituicao.br"
cat ~/.ssh/id_ed25519.pub   # copie e adicione em github.com/settings/keys
ssh -T git@github.com       # testa a conexão
```

---

## 2. Setup Inicial (Primeira Vez em uma Máquina)

### 2.1 Clonar o template com submodules

```bash
git clone --recurse-submodules git@github.com:vitalia-platform/revisao-integrativa.git
cd revisao-integrativa
```

> [!NOTE]
> Se já clonou sem `--recurse-submodules`, execute:
> `git submodule update --init --recursive`

### 2.2 Instalar o Kit de Agentes

```bash
bash kit/scripts/install.sh
```

Durante a instalação você será perguntado se deseja conectar um repositório de contexto existente:
- **Não** — cria um contexto local apenas (sem sincronização entre máquinas).
- **Sim** — informa a URL SSH do seu repositório de contexto. **Pode ser um repositório vazio**, o script criará a estrutura inicial e fará o primeiro push automaticamente.

> [!NOTE]
> `install.sh` é idempotente: pode ser rodado múltiplas vezes com segurança. A cada execução ele garante que os symlinks do kit estejam íntegros.

---

## 3. Criando seu Repositório de Trabalho

Após clonar o template, siga estes passos para transformá-lo em **seu** projeto de revisão:

### 3.1 Crie seu repositório de trabalho no GitHub

Crie um repositório **vazio** (sem README inicial):
- **Nome sugerido:** `revisao-[tema]-[ano]`
- **Exemplo:** `revisao-exercicio-digital-2026`

### 3.2 Aponte o clone para o seu repositório

```bash
git remote set-url origin git@github.com:SEU_USUARIO/revisao-[tema]-[ano].git
git push -u origin main
```

### 3.3 Crie seu repositório de contexto de sessão

O **contexto de sessão** é o que permite à IA retomar o trabalho exatamente de onde parou, mesmo ao trocar de máquina. É um repositório Git separado que sincroniza o estado da revisão.

**3a.** Crie outro repositório **vazio** no GitHub:
- **Nome sugerido:** `revisao-[tema]-contexto`
- **Exemplo:** `revisao-exercicio-digital-contexto`

**3b.** Configure o contexto no projeto:

```bash
bash kit/scripts/install.sh
# Quando solicitado, informe a URL SSH do repositório de contexto:
# git@github.com:SEU_USUARIO/revisao-[tema]-contexto.git
```

**3c.** Verifique a instalação:

```bash
python3 .agent/scripts/validate-kit.py --target .
```

Se tudo estiver correto, você verá o ambiente validado e estará pronto para trabalhar.

### 3.4 Inicie a sessão

```
/session-start
```

O agente detectará o ambiente recém-configurado e guiará você até o próximo passo: `/integrative-review`.

---

## 4. Iniciando a Revisão Integrativa (`/integrative-review`)

Este é o ponto de entrada principal do sistema. O workflow abre o **Painel Interativo de Setup** e configura toda a infraestrutura antes de qualquer processamento.

```
/integrative-review
```

O painel coletará:

| Campo | O que informar |
|---|---|
| Título provisório | Ex: "Tecnologias Digitais e Exercício Físico (2018-2026)" |
| Autores e filiação | Nomes e instituição (para o artigo final) |
| Periódico alvo | Ex: *JMIR mHealth and uHealth* |
| Pergunta norteadora (PICO/PCC) | A questão científica central da revisão |
| Recorte temporal | Ex: 2018 – 2026 |
| Bases de dados | Ex: Web of Science + Scopus via Portal CAPES |
| **Nomes das pastas de trabalho** | Exportação, amostra, lotes, saída, fichamentos |
| URL da API Ollama local | Ex: `http://ip-do-servidor:11434` |
| Modelo Ollama | Ex: `llama3.2:3b` |
| Modelo de embeddings | Ex: `nomic-embed-text` |
| Tamanho do lote | Ex: `1000` |
| Domínios de alto valor | Ex: "Educação Física Escolar", "Gamificação" |

> [!IMPORTANT]
> Todos os nomes de pasta são definidos no painel. Nenhum valor é fixo no código — tudo é gravado em `criteria_config.yaml` antes de qualquer processamento.

Após o preenchimento, o agente criará as pastas, aguardará o depósito dos dados de calibração (PDFs + CSVs) e então sugerirá os critérios de inclusão/exclusão com base na amostra. Ao aprovar, gera o `criteria_config.yaml` e inicia o pipeline PRISMA.

---

## 5. O Pipeline PRISMA (Fases da Triagem)

```
Amostra → [IA calibra critérios] → Aprovação Humana
    ↓
Lotes CSV → [Ollama local: triagem por abstract] → LOG_PRISMA_FASE1.csv
    ↓
Revisão Humana da amostra → Aprovação Humana
    ↓
DOIs aprovados → [Script multi-fonte: Unpaywall, PMC, EuropePMC, Crossref] → PDFs
    ↓
PDFs → [IA: leitura integral] → Fichamentos
    ↓
Fichamentos → [IA: síntese + categorias emergentes] → Draft do Artigo
    ↓
Draft → [Colegiado: N reuniões de revisão] → Artigo Final
```

> [!IMPORTANT]
> **HITL (Human-in-the-Loop):** O pesquisador humano é obrigatório nos pontos de aprovação do PRISMA. Nenhuma fase avança sem validação explícita. Isso garante a rastreabilidade exigida para publicação em periódicos de alto impacto.

---

## 6. Sincronização Entre Máquinas

### Ao encerrar a sessão:

```
/session-end
```

### Ao retomar em outra máquina:

```bash
# 1. Atualiza o repositório principal
git pull origin main

# 2. Atualiza o contexto da sessão
bash .agent/scripts/session-sync.sh
```

### Regra de Concorrência (ETags)

O sistema usa um Guardião de Concorrência (`.sync_lock`). Se duas máquinas tentarem sincronizar ao mesmo tempo, a segunda receberá um erro de bloqueio. **Sempre encerre a sessão antes de trocar de máquina.**

---

## 7. Mantendo o Kit de Agentes Atualizado

```bash
cd kit && git pull origin main && cd ..
bash kit/scripts/install.sh
git add kit
git commit -m "chore(kit): update agent kit to latest version"
git push origin main
```

---

## 8. Scripts do Kit — Referência

Todos os scripts estão em `kit/scripts/` e acessíveis via `bash .agent/scripts/` (symlink).

| Script | Execução | Finalidade |
|---|---|---|
| `install.sh` | `bash kit/scripts/install.sh` | **Instalação/Atualização.** Cria os symlinks do kit em `.agent/`, configura o repositório de sessão (clone ou local) e registra a máquina. Idempotente — seguro rodar múltiplas vezes. |
| `validate-kit.py` | `python3 .agent/scripts/validate-kit.py --target .` | **Auditoria de saúde.** Verifica se todos os symlinks estão corretos e se o repositório de sessão está sincronizado. Rode se suspeitar de problemas. |
| `lib_machine.py` | (interno) | **Identidade da Máquina.** Gera e persiste um ID único por máquina em `~/.vitalia/machine_id`. Registra a máquina no `machines.json` do contexto de sessão. |
| `lib_sync_guard.py` | (interno) | **Guardião de Concorrência.** Compara ETags (timestamps de commit) entre o estado local e o remoto para detectar conflitos antes de sincronizar. Impede colisões entre máquinas. |
| `session-sync.sh` | `bash .agent/scripts/session-sync.sh` | **Sincronização Completa.** Pull, consolidação de shards, commit e push do contexto de sessão. Use ao encerrar a sessão ou antes de trocar de máquina. |
| `session-resolve.sh` | `bash .agent/scripts/session-resolve.sh` | **Resolução de Conflitos.** Interface interativa para resolver divergências entre o contexto local e o remoto. Oferece opções de Pull, Push forçado, Reparo do `.git` local e Restauração da Nuvem. |
| `session-config.sh` | (interno) | **Configuração de Sessão.** Define variáveis de ambiente do agente (modelo, limites, etc.) lidas do `criteria_config.yaml`. |
| `session-consolidate.py` | (interno, chamado por `session-sync.sh`) | **Consolidação.** Mescla os arquivos de shard individuais (uma máquina por arquivo) no `CONTEXT.md` principal. |

### Fluxo do `install.sh` em detalhes

```
Clone do template
    ↓
bash kit/scripts/install.sh
    ↓
├─ Cria/atualiza symlinks: .agent/{agents,rules,skills,workflows,templates,scripts}
├─ Se .agent/session/.git não existe:
│   ├─ Sim: Clone do repo de contexto informado
│   │   └─ Se repo vazio: cria CONTEXT.md + commit inicial + push
│   └─ Não: git init local com estrutura mínima
├─ Registra máquina em machines.json
└─ Roda validate-kit.py (auditoria final)
```

> [!TIP]
> Em caso de qualquer falha após o clone, o `install.sh` cria automaticamente um contexto local de fallback. Isso significa que você nunca fica bloqueado — pode trabalhar localmente e conectar ao remoto depois via `session-resolve.sh` (opção 2 ou 4).

---

## 9. Troubleshooting

### Contexto não sincroniza

```bash
git add . && git commit -m "wip: salvar estado antes de sincronizar"
bash .agent/scripts/session-sync.sh "Sua mensagem"
```

### Repositório de contexto corrompido

```bash
# Reconfigura o remote e faz pull
cd .agent/session
git remote set-url origin git@github.com:SEU_USUARIO/revisao-[tema]-contexto.git
git pull origin main --rebase
cd ../..
```

```bash
# Reset total: remove e reinstala
rm -rf .agent/session
bash kit/scripts/install.sh
```

### Symlinks do kit quebrados

```bash
python3 .agent/scripts/validate-kit.py --target .
bash kit/scripts/install.sh
```

### API do Ollama não responde

Verifique se o servidor Docker está rodando e se o endereço no `criteria_config.yaml` está correto. Consulte `Hardware.md` para a configuração do servidor local.

---

## 9. Estrutura de Branches

| Branch | Propósito |
|---|---|
| `main` | Estado estável, aprovado pelo colegiado. |
| `draft/fase-N` | Rascunhos da fase N da triagem ou do artigo. |
| `review/colegiado-N` | Branch para revisão e comentários do colegiado. |

---

## 10. Referências

| Documento | Localização | Propósito |
|---|---|---|
| Manual do Kit de Agentes | `kit/MANUAL.md` | Catálogo completo de agentes, skills e workflows |
| Sumário Executivo | `inicio/00_SUMARIO_EXECUTIVO.md` | Identidade do estudo e estado PRISMA |
| Roteiro de Trabalho da IA | `inicio/ROTEIRO_IA_REVISAO.md` | Instruções detalhadas por fase para os agentes |
| Template de Configuração | `inicio/criteria_config.template.yaml` | Modelo base para o `criteria_config.yaml` |
| ADR-001 (Rigor Metodológico) | `inicio/ADR-001-Rigor-Revisao-Academica.md` | Decisões arquiteturais que regem a Clean Room |
| Roteiro de Busca CAPES | `inicio/ROTEIRO_BUSCA_CAPES.md` | Passo a passo para exportar dados via acesso institucional |
| Configuração do Hardware | `inicio/Hardware.md` | Especificações do servidor local de inferência |

---

> _Este repositório opera sob a metodologia Mendes, Silveira e Galvão (2008) e segue as diretrizes PRISMA para máxima rastreabilidade e publicabilidade._
