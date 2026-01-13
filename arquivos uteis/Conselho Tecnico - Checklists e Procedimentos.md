---
up: "[[Efforts/Projects/Active/Log Projeto Transcription Flow]]"
related:
  - "[[+/Framework de Desenvolvimento com IA - Melhores Praticas]]"
  - "[[+/Framework de Auditoria de Qualidade em Software]]"
created: 2026-01-09
---

# Conselho Tecnico - Checklists e Procedimentos

> [!info] Proposito deste Documento
> Centralizar os checklists e procedimentos de avaliacao de todos os 13 membros do Conselho Tecnico.
> Este documento e a **fonte unica de verdade** para procedimentos de auditoria.
>
> **Outros documentos devem REFERENCIAR este**, nao duplicar conteudo.

---

## Indice

1. [[#Principio Fundamental - Diagnostico Baseado em Evidencias]]
2. [[#Visao Geral do Conselho]]
3. [[#Participacao por Fase]]
4. [[#Checklists por Membro]]
   - [[#1 Head de Infraestrutura]]
   - [[#2 Head de QA]]
   - [[#3 Head de Qualidade Tecnica]]
   - [[#4 Head de Seguranca]]
   - [[#5 Head de SRE Observabilidade]]
   - [[#6 Head de Performance]]
   - [[#7 Head de Arquitetura]]
   - [[#8 Head de Estrategia]]
   - [[#9 Head de Tecnologias]]
   - [[#10 Head de Integracao E2E]]
   - [[#11 Head de Aceitacao UAT]]
   - [[#12 Head de Governanca de Docs]]
   - [[#13 Head de Projeto PO]]
5. [[#Head de UX UI Condicional]]
6. [[#Formato de Avaliacao]]
7. [[#Licoes Aprendidas]]

---

## Principio Fundamental - Diagnostico Baseado em Evidencias

> [!danger] Regra Zero - Aplicavel a TODAS as Acoes
> **NENHUMA acao deve ser tomada sem diagnostico baseado em evidencias.**
>
> Este principio aplica-se a:
> - Auditorias de sprint
> - Auditorias de codigo
> - Implementacao de features novas
> - Correcoes de bugs
> - Qualquer decisao tecnica

### O que e Diagnostico Baseado em Evidencias?

| Tipo | Definicao | Exemplo |
|------|-----------|---------|
| **Evidencia Presente** | Dados, logs, testes, outputs que comprovam estado atual | "Log mostra erro 401 na linha X" |
| **Evidencia Futura (Benchmarking)** | Pesquisa que comprova que outros resolvem problema similar | "Biblioteca Y e usada por 1000+ projetos para isso" |

### Quando Aplicar

| Fase | Como Aplicar |
|------|--------------|
| **PRE-SPRINT** | Benchmarking obrigatorio para features novas (Head #9 Tecnologias) |
| **DURANTE** | Evidencias de teste antes de declarar "funciona" (Head #10 E2E) |
| **POS-SPRINT** | Auditorias verificam com evidencias, nao suposicoes |
| **CORRECAO** | Diagnosticar causa raiz ANTES de propor solucao |

### Checklist de Diagnostico (Obrigatorio)

Antes de qualquer acao, responder:

| # | Pergunta | Resposta Aceitavel |
|---|----------|-------------------|
| D1 | Qual evidencia comprova o problema? | Log, erro, teste falhando, output incorreto |
| D2 | Qual evidencia comprova que a solucao funciona? | Teste passando, output correto, comportamento observado |
| D3 | Se feature nova: qual evidencia de que outros fazem assim? | Benchmark, docs, projetos open source |
| D4 | Quais suposicoes estou fazendo SEM evidencia? | Listar para validar |

### Anti-Padroes (PROIBIDO)

| Anti-Padrao | Exemplo | Correcao |
|-------------|---------|----------|
| "Acho que..." | "Acho que o problema e X" | "O log mostra que o problema e X" |
| "Deve funcionar" | "Mudei Y, deve funcionar agora" | "Mudei Y, teste Z confirma que funciona" |
| "Vou implementar X" | Sem pesquisa previa | "Pesquisa mostra que X e padrao comum" |
| "Isso resolve" | Sem verificar causa raiz | "Diagnostico mostra causa raiz em W" |

### Origem deste Principio

**Contexto:** Sprint 11.4 entregou codigo que passava em auditorias mas nao funcionava para o usuario.

**Causa Raiz:** Auditorias verificavam CODIGO (sintaxe, padroes) mas nao verificavam COMPORTAMENTO (funciona? esta acessivel?).

**Solucao:** Todo membro do Conselho deve verificar com EVIDENCIAS:
- Nao basta dizer "codigo esta correto"
- Deve mostrar "teste X prova que funciona"
- Deve verificar "usuario consegue acessar"

---

## Visao Geral do Conselho

| # | Lideranca | Foco Principal | Atua em |
|---|-----------|----------------|---------|
| 1 | Head de Infraestrutura | Retry, timeouts, deploy, scale, validacao .env | Auditoria |
| 2 | Head de QA | Validacao, testes unitarios + integracao, consistencia | Auditoria |
| 3 | Head de Qualidade Tecnica | Duplicacao, funcoes longas, separacao de responsabilidades | Auditoria |
| 4 | Head de Seguranca | Path traversal, injection, sanitizacao | Auditoria |
| 5 | Head de SRE/Observabilidade | Logging, metricas, correlation ID | Auditoria |
| 6 | Head de Performance | Async, streaming, cache, memoria | Auditoria |
| 7 | Head de Arquitetura | Modularidade, reusabilidade, integracoes futuras | Auditoria |
| 8 | Head de Estrategia | Gargalos, sinergia, ROI, reuso | Auditoria |
| 9 | Head de Tecnologias | Pesquisa pre-sprint, avaliar alternativas | PRE-SPRINT |
| 10 | Head de Integracao/E2E | Testes integrados, comunicacao entre servicos | Durante + Auditoria |
| 11 | Head de Aceitacao/UAT | Fluxos de usuario, comportamento esperado | Auditoria |
| 12 | Head de Governanca de Docs | Sincronizacao, redundancia, obsolescencia, links | Auditoria |
| 13 | Head de Projeto/PO | Alinhamento PRD, priorizacao, status, bloqueadores | PRE + Auditoria |

---

## Participacao por Fase

| Fase | Quem Participa | Responsabilidade |
|------|----------------|------------------|
| PRE-SPRINT | #9 (Tecnologias) + #13 (Projeto) | Pesquisa, priorizacao, escopo |
| DURANTE | #10 (Integracao/E2E) | Testes de integracao (Regra 5.5) |
| POS-SPRINT | 12 liderancas (#1-8, #10-13) | Auditoria completa |

> [!note] Nota
> Head de Tecnologias (#9) NAO participa da auditoria POS-SPRINT pois seu papel e exclusivo de PRE-SPRINT.

---

## Checklists por Membro

### 1 Head de Infraestrutura

**Fase:** POS-SPRINT (Auditoria)

| # | Item | Verificacao | Severidade |
|---|------|-------------|------------|
| 1 | Retry com backoff | Chamadas externas tem retry exponencial? | MUST |
| 2 | Timeouts configurados | Todas as operacoes tem timeout definido? | MUST |
| 3 | Health checks | Endpoints /health implementados e funcionais? | MUST |
| 4 | Validacao .env | Todas as variaveis de ambiente documentadas e validadas no startup? | MUST |
| 5 | Graceful shutdown | Servicos tratam SIGTERM corretamente? | SHOULD |
| 6 | Resource limits | Limites de memoria/CPU definidos no docker-compose? | SHOULD |
| 7 | Volume persistence | Dados persistentes mapeados para volumes? | SHOULD |
| 8 | Network isolation | Servicos em redes apropriadas? | COULD |
| 9 | Escalabilidade | Servico pode escalar horizontalmente? | COULD |

---

### 2 Head de QA

**Fase:** POS-SPRINT (Auditoria)

| # | Item | Verificacao | Severidade |
|---|------|-------------|------------|
| 1 | Testes unitarios | Funcoes criticas tem testes? | MUST |
| 2 | Testes de integracao | Endpoints tem testes de integracao? | MUST |
| 3 | Cobertura minima | Cobertura >= 70% em modulos novos? | SHOULD |
| 4 | Casos de borda | Edge cases testados? | SHOULD |
| 5 | Fixtures reutilizaveis | Dados de teste organizados? | SHOULD |
| 6 | Mocks apropriados | Dependencias externas mockadas? | SHOULD |
| 7 | Testes de regressao | Bugs corrigidos tem teste de regressao? | SHOULD |
| 8 | CI/CD integrado | Testes rodam automaticamente no CI? | COULD |

---

### 3 Head de Qualidade Tecnica

**Fase:** POS-SPRINT (Auditoria)

| # | Item | Verificacao | Severidade |
|---|------|-------------|------------|
| 1 | Duplicacao de codigo | DRY - codigo repetido extraido? | MUST |
| 2 | Funcoes longas | Funcoes com mais de 50 linhas decompostas? | SHOULD |
| 3 | Separacao de responsabilidades | Uma funcao = uma responsabilidade? | MUST |
| 4 | Naming conventions | Nomes descritivos e consistentes? | SHOULD |
| 5 | Magic numbers | Constantes nomeadas em vez de numeros soltos? | SHOULD |
| 6 | Dead code | Codigo nao utilizado removido? | SHOULD |
| 7 | Complexidade ciclomatica | Funcoes com complexidade <= 10? | COULD |
| 8 | Type hints | Funcoes tem anotacoes de tipo? | SHOULD |

---

### 4 Head de Seguranca

**Fase:** POS-SPRINT (Auditoria)

| # | Item | Verificacao | Severidade |
|---|------|-------------|------------|
| 1 | Path traversal | Caminhos de arquivo sanitizados? | MUST |
| 2 | SQL injection | Queries parametrizadas? | MUST |
| 3 | Command injection | Inputs validados antes de subprocess? | MUST |
| 4 | XSS prevention | Outputs escapados em HTML? | MUST |
| 5 | Secrets exposure | Sem secrets hardcoded no codigo? | MUST |
| 6 | Autenticacao | Endpoints protegidos tem auth? | MUST |
| 7 | Autorizacao | Verificacao de permissoes implementada? | SHOULD |
| 8 | CORS configurado | Origens permitidas restritas? | SHOULD |
| 9 | Rate limiting | Protecao contra abuso implementada? | SHOULD |
| 10 | Input validation | Todos os inputs validados? | MUST |

---

### 5 Head de SRE Observabilidade

**Fase:** POS-SPRINT (Auditoria)

| # | Item | Verificacao | Severidade |
|---|------|-------------|------------|
| 1 | Logging estruturado | Logs em JSON com campos padronizados? | MUST |
| 2 | Niveis de log | INFO, WARNING, ERROR usados corretamente? | SHOULD |
| 3 | Correlation ID | Request ID propagado entre servicos? | SHOULD |
| 4 | Metricas expostas | Endpoint /metrics com Prometheus? | COULD |
| 5 | Tracing distribuido | Spans criados para operacoes principais? | COULD |
| 6 | Alertas configurados | Thresholds definidos para erros? | COULD |
| 7 | Log rotation | Logs nao crescem indefinidamente? | SHOULD |
| 8 | Error context | Excecoes logadas com contexto suficiente? | MUST |

---

### 6 Head de Performance

**Fase:** POS-SPRINT (Auditoria)

| # | Item | Verificacao | Severidade |
|---|------|-------------|------------|
| 1 | Operacoes async | I/O usa async/await? | MUST |
| 2 | Streaming response | Arquivos grandes usam streaming? | MUST |
| 3 | Cache implementado | Resultados reutilizaveis cacheados? | SHOULD |
| 4 | Memory leaks | Sem vazamentos de memoria obvios? | MUST |
| 5 | Lazy loading | Recursos carregados sob demanda? | SHOULD |
| 6 | Connection pooling | Pools de conexao reutilizados? | SHOULD |
| 7 | Batch processing | Operacoes em lote onde aplicavel? | COULD |
| 8 | Profiling | Gargalos identificados e documentados? | COULD |

---

### 7 Head de Arquitetura

**Fase:** POS-SPRINT (Auditoria)

| # | Item | Verificacao | Severidade |
|---|------|-------------|------------|
| 1 | Modularidade | Codigo organizado em modulos coesos? | MUST |
| 2 | Acoplamento baixo | Dependencias entre modulos minimizadas? | SHOULD |
| 3 | Interfaces claras | Contratos entre servicos bem definidos? | MUST |
| 4 | Reusabilidade | Componentes podem ser reutilizados? | SHOULD |
| 5 | Extensibilidade | Facil adicionar novas funcionalidades? | SHOULD |
| 6 | Padrao consistente | Mesmo padrao em todo o projeto? | SHOULD |
| 7 | Documentacao arquitetural | Decisoes documentadas em ADRs? | COULD |
| 8 | Separacao de camadas | Presentation/Business/Data separados? | SHOULD |

---

### 8 Head de Estrategia

**Fase:** POS-SPRINT (Auditoria)

| # | Item | Verificacao | Severidade |
|---|------|-------------|------------|
| 1 | Identificacao de gargalos | Pontos de bloqueio mapeados? | SHOULD |
| 2 | Sinergia entre servicos | Servicos se complementam bem? | SHOULD |
| 3 | ROI da implementacao | Esforco justifica o valor entregue? | MUST |
| 4 | Reuso de assets | Codigo/libs existentes reutilizados? | SHOULD |
| 5 | Divida tecnica | Debitos identificados e registrados? | MUST |
| 6 | Riscos mapeados | Riscos tecnicos documentados? | SHOULD |
| 7 | Dependencias criticas | Pontos unicos de falha identificados? | SHOULD |
| 8 | Alinhamento com roadmap | Sprint avanca em direcao aos objetivos? | MUST |

---

### 9 Head de Tecnologias

**Fase:** PRE-SPRINT (Pesquisa)

> [!important] Regra de Ouro
> **Priorizar solucoes GRATUITAS/OPEN SOURCE sempre que atingirem nota >= 9/10 nos criterios.**

| # | Item | Verificacao | Severidade |
|---|------|-------------|------------|
| 1 | WebSearch atualizado | Pesquisa com ano atual (2026)? | MUST |
| 2 | Fontes consultadas | GitHub, PyPI, MTEB, Papers, HuggingFace? | MUST |
| 3 | Alternativas listadas | Minimo 3 opcoes avaliadas? | MUST |
| 4 | Criterios aplicados | 8 criterios com notas? | MUST |
| 5 | Benchmark referenciado | Dados quantitativos incluidos? | SHOULD |
| 6 | Compatibilidade Windows | Solucao funciona sem WSL? | MUST |
| 7 | Licenca verificada | Open source preferido, licenca compativel? | SHOULD |
| 8 | Relatorio documentado | Conclusao com justificativa? | MUST |

**8 Criterios de Avaliacao (todos >= 9/10 para aprovar):**

| Criterio | Descricao | Peso |
|----------|-----------|------|
| Qualidade | Resultado final, precisao, robustez | 15% |
| Seguranca | Vulnerabilidades, compliance, privacidade | 15% |
| Performance | Velocidade, latencia, throughput | 10% |
| Confiabilidade | Uptime, recuperacao, consistencia | 10% |
| Produtividade | Facilidade de uso, docs, curva de aprendizado | 15% |
| Adaptabilidade | Flexibilidade, extensibilidade, integracao | 10% |
| Economia | Custo total, gratuito vs pago, recursos | 15% |
| Alavancagem | Reuso, sinergia com existente, valor agregado | 10% |

---

### 10 Head de Integracao E2E

**Fase:** DURANTE (Testes) + POS-SPRINT (Auditoria)

| # | Item | Verificacao | Severidade |
|---|------|-------------|------------|
| 1 | Servico sobe isolado | `docker-compose up -d [servico]` funciona? | MUST |
| 2 | Health check responde | `curl /health` retorna 200? | MUST |
| 3 | Endpoint principal funciona | Request/response conforme esperado? | MUST |
| 4 | Logs sem erros | `docker logs` limpo? | MUST |
| 5 | Comunicacao entre servicos | API Gateway roteia corretamente? | MUST |
| 6 | Fluxo end-to-end | Pipeline completo funciona? | MUST |
| 7 | Tratamento de erros | Erros propagados corretamente? | SHOULD |
| 8 | Timeout entre servicos | Timeouts configurados nas chamadas? | SHOULD |
| 9 | Retry entre servicos | Falhas transitorias tratadas? | SHOULD |

---

### 11 Head de Aceitacao UAT

**Fase:** POS-SPRINT (Auditoria)

| # | Item | Verificacao | Severidade |
|---|------|-------------|------------|
| 1 | Fluxo principal | Usuario consegue completar tarefa principal? | MUST |
| 2 | Feedback visual | Usuario sabe o que esta acontecendo? | MUST |
| 3 | Estados de loading | Indicadores de progresso visiveis? | SHOULD |
| 4 | Mensagens de erro | Erros sao claros e acionaveis? | MUST |
| 5 | Validacao de inputs | Campos invalidos sao rejeitados com feedback? | SHOULD |
| 6 | Confirmacao de acoes | Acoes destrutivas pedem confirmacao? | SHOULD |
| 7 | Consistencia visual | Interface segue padroes do projeto? | SHOULD |
| 8 | Acessibilidade basica | Contraste, tamanho de fonte adequados? | COULD |

---

### 12 Head de Governanca de Docs

**Fase:** POS-SPRINT (antes do push)

| # | Item | Verificacao | Severidade |
|---|------|-------------|------------|
| 1 | Sincronizacao entre docs | LOG.md, PLANO, Log Obsidian consistentes? | MUST |
| 2 | Informacoes obsoletas | Referencias a sprints concluidas arquivadas? | SHOULD |
| 3 | Redundancia | Mesma informacao em multiplos lugares? | SHOULD |
| 4 | Docs provisorios | Sprint precisa de nota temporaria em `docs/sprints/`? | COULD |
| 5 | Concisao docs-chave | LOG.md, CONTRIBUTING.md estao enxutos? | SHOULD |
| 6 | Changelog atualizado | Versoes, datas, mudancas registradas? | SHOULD |
| 7 | Links funcionais | Referencias apontam para arquivos existentes? | MUST |
| 8 | Nomenclatura | Nomes de arquivos seguem padrao? | SHOULD |

---

### 13 Head de Projeto PO

**Fase:** PRE-SPRINT + POS-SPRINT

#### PRE-SPRINT

| # | Item | Verificacao | Severidade |
|---|------|-------------|------------|
| 1 | Alinhamento com PRD | Sprint entrega valor alinhado aos requisitos? | MUST |
| 2 | Priorizacao correta | E a sprint mais importante agora? | MUST |
| 3 | Escopo definido | Entregaveis claros? Evitar scope creep? | MUST |
| 4 | Dependencias mapeadas | Bloqueadores identificados? | SHOULD |

#### POS-SPRINT

| # | Item | Verificacao | Severidade |
|---|------|-------------|------------|
| 5 | Estado Atual atualizado | Log Obsidian reflete realidade? | MUST |
| 6 | Bloqueadores documentados | Issues/pendencias registrados? | MUST |
| 7 | Progresso roadmap | % de conclusao por fase atualizado? | SHOULD |
| 8 | Alteracoes temporarias | Secao de registro atualizada? | SHOULD |
| 9 | Debitos tecnicos | Novos debitos registrados? | SHOULD |
| 10 | Comunicacao | Resumo da sprint legivel para stakeholders? | SHOULD |

---

## Head de UX UI Condicional

**Ativado em:** Sprints com interface (tipos B, C, D)

| # | Item | Verificacao | Severidade |
|---|------|-------------|------------|
| 1 | Fluxo de usuario | Caminho feliz intuitivo? | MUST |
| 2 | Usabilidade | Acoes principais acessiveis em <= 3 cliques? | SHOULD |
| 3 | Feedback visual | Estados hover, active, disabled claros? | SHOULD |
| 4 | Estados de erro | Erros nao quebram a UI? | MUST |
| 5 | Loading states | Usuario sabe quando algo esta processando? | MUST |
| 6 | Responsividade | Layout adapta a diferentes tamanhos? | COULD |
| 7 | Consistencia | Mesmo padrao visual em toda a aplicacao? | SHOULD |
| 8 | Acessibilidade | Navegacao por teclado funciona? | COULD |

---

## Formato de Avaliacao

### Severidade dos Issues

| Nivel | Significado | Bloqueia Sprint? |
|-------|-------------|------------------|
| MUST | Obrigatorio, critico | SIM |
| SHOULD | Importante, recomendado | SIM |
| COULD | Desejavel, melhoria | SIM (apos MUST/SHOULD) |

> [!danger] Nota Minima
> A sprint so e aprovada com nota **>= 9/10** em TODOS os criterios aplicaveis.
> Issues de qualquer severidade devem ser tratados antes do push.

### Template de Avaliacao

```text
AVALIACAO DO CONSELHO TECNICO
Sprint: [numero e nome]
Data: [YYYY-MM-DD]

## Notas por Lideranca
| # | Lideranca | Nota | Issues |
|---|-----------|------|--------|
| 1 | Infraestrutura | X/10 | [lista] |
| 2 | QA | X/10 | [lista] |
| ... | ... | ... | ... |

## Resumo
- Total MUST: X
- Total SHOULD: X
- Total COULD: X
- Nota Final: X/10
- Status: APROVADO/REPROVADO
```

---

## Licoes Aprendidas

Esta secao documenta falhas de auditoria para evitar recorrencias.

### LA-001: Sprint 11.4 - Interface Desktop PyQt (2026-01-09)

**Contexto:** Sprint entregou interface PyQt (tf-desktop) que passou na auditoria de codigo, mas nao estava acessivel ao usuario final.

**Problema Identificado:**

- Usuario pediu interface CLI terminal (estilo `processar_arquivo.py`)
- Foi entregue interface grafica PyQt
- Interface grafica nao era acessivel a partir do launcher
- Auditoria aprovou codigo sem verificar integracao e acessibilidade

**Liderancas que Falharam:**

| #  | Lideranca              | O que Deveria Ter Feito                                                                                                    |
|----|------------------------|----------------------------------------------------------------------------------------------------------------------------|
| 10 | Head de Integracao/E2E | Verificar se tf-desktop e acessivel pelo launcher. Item #6 "Fluxo end-to-end funciona?"                                    |
| 11 | Head de Aceitacao/UAT  | Testar se usuario consegue acessar TODAS as interfaces entregues. Item #1 "Usuario consegue completar tarefa principal?"   |
| 13 | Head de Projeto/PO     | Questionar se entrega corresponde ao pedido original. Item #1 "Sprint entrega valor alinhado aos requisitos?"              |

**Causa Raiz:**

A auditoria focou apenas na **corretude do codigo** (sintaxe, padroes, testes) e ignorou:

1. **Integracao**: A funcionalidade esta acessivel?
2. **Aceitacao**: A funcionalidade corresponde ao pedido?

**Acao Corretiva:**

1. Adicionado `tf menu` - menu CLI interativo
2. Adicionado opcoes no systray do launcher: "Abrir Desktop (PyQt)" e "Abrir CLI Menu"
3. Corrigido erro "Nao foi possivel verificar" - mensagem agora e mais clara

**Novas Regras para Evitar Recorrencia:**

> [!warning] Regra de Ouro - Verificacao de Acessibilidade
> **TODA entrega deve responder SIM a estas 3 perguntas:**
>
> 1. O usuario consegue ACESSAR a funcionalidade? (Integracao #10)
> 2. O usuario consegue USAR a funcionalidade? (UAT #11)
> 3. A funcionalidade CORRESPONDE ao que foi pedido? (Projeto #13)

**Checklist Adicional para #10 (Integracao):**

- [ ] Nova funcionalidade esta acessivel pelo ponto de entrada principal (launcher, CLI, menu)?
- [ ] Usuario nao precisa de conhecimento tecnico especial para acessar?

**Checklist Adicional para #11 (UAT):**

- [ ] Todas as interfaces entregues na sprint foram testadas end-to-end?
- [ ] Fluxo de acesso documentado ou obvio?

**Checklist Adicional para #13 (Projeto):**

- [ ] Entrega corresponde exatamente ao que foi pedido?
- [ ] Se houve mudanca de escopo, foi comunicada e aprovada?

---

### LA-002: Sprint 11.1.6 - Pesquisa Obrigatoria Antes de Solucoes (2026-01-09)

**Contexto:** Sprint de bugfix para menu Textual. IA tentou multiplas solucoes sem pesquisar, desperdicando tempo e frustrando o usuario.

**Problema Identificado:**

- Bug: Menu Textual nao abria quando lancado via pythonw.exe
- IA tentou 5+ solucoes diferentes sem sucesso
- Solucao foi encontrada em 5 minutos quando pesquisou no GitHub
- Pesquisa revelou que outros ja haviam resolvido o mesmo problema

**Tentativas Falhas (SEM pesquisa):**

| # | Tentativa | Resultado |
|---|-----------|-----------|
| 1 | Mudar de cmd para Windows Terminal (wt.exe) | Erro de sintaxe com espacos |
| 2 | Usar CREATE_NEW_CONSOLE | sys.stdout continuava None |
| 3 | Criar batch file temporario | Mesmo problema |
| 4 | Usar os.startfile() | Mesmo problema |
| 5 | Ajustar quotes no comando | Mesmo problema |

**Solucao (COM pesquisa):**

Pesquisa no GitHub revelou:
- [Textual Discussion #335](https://github.com/Textualize/textual/discussions/335): Windows blank screen issue
- [desktop-app repo](https://github.com/chrisjbillington/desktop-app): Solucao para pythonw.exe

**Causa Raiz encontrada:** `sys.executable` retorna `pythonw.exe` (GUI, sem console) em vez de `python.exe`. Textual REQUER console real.

**Solucao correta:** Usar `python.exe` do venv explicitamente, NAO `sys.executable`.

**Liderancas que Deveriam Ter Atuado:**

| # | Lideranca | O que Deveria Ter Feito |
|---|-----------|------------------------|
| 9 | Head de Tecnologias | Pesquisar ANTES de propor solucoes. Regra 3 aplica-se a bugfixes tambem! |
| Todos | Principio Fundamental | Aplicar "Evidencia Futura (Benchmarking)" para bugs, nao so features |

**Nova Regra - PESQUISA OBRIGATORIA PARA BUGS:**

> [!danger] Regra Cogente: Pesquisa Antes de Solucao
> **ANTES de tentar QUALQUER solucao para um bug:**
>
> 1. **Diagnosticar** - Ler logs, identificar erro especifico
> 2. **Pesquisar** - WebSearch, GitHub Issues, Stack Overflow
> 3. **Alavancar** - Encontrar como OUTROS resolveram
> 4. **Implementar** - So entao propor/implementar solucao
>
> **Maximo de 2 tentativas sem pesquisa.** Na terceira falha, pesquisa e OBRIGATORIA.
>
> **Anti-padrao PROIBIDO:** "Vou tentar X... nao funcionou. Vou tentar Y... nao funcionou. Vou tentar Z..."

**Checklist de Pesquisa para Bugs:**

| # | Acao | Fonte |
|---|------|-------|
| 1 | Copiar mensagem de erro exata | Log, console |
| 2 | Pesquisar erro + biblioteca + plataforma | WebSearch |
| 3 | Verificar GitHub Issues da biblioteca | `site:github.com [biblioteca] [erro]` |
| 4 | Verificar Stack Overflow | `site:stackoverflow.com [erro]` |
| 5 | Documentar solucao encontrada | Com link da fonte |

**Impacto:**

- Tempo perdido sem pesquisa: ~40 minutos
- Tempo para resolver com pesquisa: ~5 minutos
- Frustracao do usuario: ALTA
- Licao: Pesquisa NAO e perda de tempo, e ECONOMIA de tempo

---

> [!tip] Atualizacao deste Documento
> Quando o Conselho for alterado (novos membros, novos criterios), atualizar:
> 1. Este documento (fonte primaria)
> 2. Log Projeto Transcription Flow (referencia)
> 3. PLANO_MICROSERVICES.md secao 7 (referencia)
