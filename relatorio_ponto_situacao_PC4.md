# Relatório de Ponto de Situação - Ponto de Controlo 4 (PC4)
**Projeto:** My Closet App  
**Unidade Curricular:** Projeto IV | Licenciatura em Engenharia Informática | IPVC  
**Autores:** Diogo Viana (29195) e Gonçalo Oliveira (29198)  
**Orientador:** Professor Doutor Miguel Cruz  
**Data:** 29 de Maio de 2026  

---

## 1. Introdução e Enquadramento
Este documento constitui o relatório de ponto de situação do projeto **My Closet App** para o **Ponto de Controlo 4 (PC4)**. O objetivo deste documento é relatar o progresso real e o estado operacional do sistema, focando-se na transição das fundações arquiteturais apresentadas no PC3 para a integração e validação prática da Inteligência Artificial (VLM).

---

## 2. Resumo Executivo do Estado do Projeto
O projeto **My Closet App** encontra-se na sua fase final de consolidação, com todas as componentes do pipeline inteligente operacionais e testadas. 

*   **Backend (FastAPI + Python):** 100% operacional. A integração com o modelo visual local (LLaVA via Ollama) foi concluída com sucesso. Foi adicionada uma camada robusta de validação de recomendações em três níveis para garantir a integridade dos dados e prevenir alucinações.
*   **Frontend (React + TypeScript):** Funcional. O dashboard foi atualizado para comunicar com os novos endpoints de IA, permitindo a exibição do manequim interativo dividido por camadas base, isolamento e exterior.
*   **Base de Dados e Armazenamento (Supabase):** Totalmente integrado, gerindo autenticação, tabelas relacionais de peças, histórico de uso e armazenamento seguro de ficheiros de imagem com URLs assinados.

---

## 3. Estado de Desenvolvimento das Funcionalidades

| Funcionalidade / Componente | Estado Atual | Descrição / Detalhe Técnico |
| :--- | :--- | :--- |
| **Autenticação e Perfil** | **Concluído** | Login/registo via Supabase. Perfil de utilizador editável. |
| **Perfil Masculino** | **Concluído** | Implementação de regras e estilos de guarda-roupa específicos para perfis masculinos. |
| **Catálogo e CRUD** | **Concluído** | Adição, edição e eliminação de peças com upload de imagem e classificação automática (MobileNet no cliente). |
| **Integração VLM (LLaVA)** | **Concluído** | Conexão local estável via Ollama. Envio de imagens codificadas em Base64 e prompts estruturados. |
| **Pipeline de Validação** | **Concluído** | Validação em 3 níveis (Existência/Estado, Clima/Temperatura e Camadas do Outfit) com lógica de *retry*. |
| **Manutenção de Regras** | **Concluído** | Sistema de *fallback* automático para o motor de regras determinístico caso a IA falhe. |
| **Histórico de Uso** | **Concluído** | Gravação de métricas de utilização das peças (`usage_service.py`) para controlo de fadiga e repetição de outfits. |
| **Manequim Visual** | **Concluído** | Renderização dinâmica do outfit recomendado por camadas (Base, Insulation, Outer, Shoes). |
| **Planeador de Viagens** | **Concluído** | Gerador automático de listas de bagagem com base no clima e duração da viagem. |
| **MLOps (MLflow)** | **Concluído** | Monitorização de tempos de inferência e versões de prompts. |

---

## 4. Evolução e Trabalho Desenvolvido (Pós-PC3)

### 4.1. Operacionalização do VLM Local
No PC3, a integração com o modelo visual LLaVA encontrava-se em fase preparatória com stubs de simulação. No PC4, o pipeline local foi totalmente ativado usando a API do **Ollama** (`http://localhost:11434/v1/chat/completions`). O sistema envia a descrição textual do contexto climático e as imagens reais das peças do utilizador codificadas em Base64 através do `ImagePreprocessingService`.

### 4.2. Implementação da Camada de Validação
Para mitigar o problema das alucinações dos modelos de linguagem, foi desenvolvida a classe de validação no `RecommendationService`:
*   **Validação de IDs:** Garante que a IA apenas sugere peças que realmente existem no guarda-roupa do utilizador.
*   **Filtro de Estado:** Bloqueia a recomendação de peças que estejam marcadas na base de dados como "sujas" ou "danificadas".
*   **Compatibilidade Térmica:** Avalia se o intervalo de temperatura confortável de cada peça é compatível com a temperatura atual do local.
*   **Lógica de Recuperação (*Retry*):** Se o outfit gerado falhar na validação, o backend efetua uma segunda chamada à IA, injetando os erros identificados e restringindo o inventário apenas a peças limpas e compatíveis com a meteorologia.

### 4.3. Implementação do Perfil Masculino
Foi adicionado suporte ao perfil masculino no frontend e backend, garantindo que o motor de recomendações e a renderização do manequim se ajustam dinamicamente às preferências de vestuário e categorização masculina.

---

## 5. Caso de Uso Prático (Exemplo de Funcionamento)
Um pedido típico de recomendação de outfit no estado atual do PC4 segue o seguinte fluxo validado:
1.  **Entrada:** Utilizador solicita outfit para clima de 20°C, céu limpo, com estilo casual.
2.  **Invocação LLaVA:** O modelo analisa as peças disponíveis.
3.  **Resultado da IA:**
    *   *Sugestão:* Camisola de Algodão (ID `base_001`), Calças Chino (ID `outer_003`), Ténis (ID `outer_004`).
    *   *Justificação da IA:* "Para uma temperatura agradável de 20°C, uma camisola leve de algodão oferece conforto ideal. As calças chino pretas e os ténis brancos mantêm um estilo casual e limpo para o dia."
4.  **Validação:** O sistema valida que as 3 peças pertencem ao utilizador, estão limpas e adequadas para a temperatura. O outfit é aprovado e renderizado no ecrã com `model_used: "llava"`.

---

## 6. Desafios Superados
1.  **Gestão de Memória e OOM (Out of Memory):** Modelos visuais locais exigem bastantes recursos. Limitou-se o processamento a um máximo de 6 imagens por pedido e otimizou-se a resolução das imagens no pré-processamento.
2.  **Tratamento de Ficheiros de Cache e Conflitos:** Resolução de conflitos de git relativos a ficheiros de compilação do Python (`__pycache__`) e logs locais de testes de VLM que bloqueavam a sincronização do repositório.

---

## 7. Próximos Passos (Até à Entrega Final)
Com a aplicação totalmente funcional, os trabalhos até à entrega final do projeto centrar-se-ão em:
1.  **Otimização de Performance:** Reduzir o tempo de resposta da inferência local do LLaVA (atualmente entre 5 a 15 segundos dependendo do hardware).
2.  **Refinamento de Prompts:** Ajustar as restrições estéticas no `prompt_service.py` para melhorar a harmonia de cores recomendada pela IA.
3.  **Elaboração da Documentação Final:** Redação do relatório de tese final e preparação da demonstração prática para a defesa do projeto.
