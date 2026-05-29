# Guia de Conteúdo para Apresentação - Ponto de Controlo 4 (PC4)
**Projeto:** My Closet App  
**Autores:** Diogo Viana (29195) e Gonçalo Oliveira (29198)  
**Orientador:** Professor Doutor Miguel Cruz  
**Unidade Curricular:** Projeto IV | Licenciatura em Engenharia Informática | IPVC  
**Ano Letivo:** 2025/2026  

---

## 📋 Resumo das Atualizações do PC3 para o PC4
No Ponto de Controlo 4 (Apresentação Final / Consolidação), o foco passa de "Preparação e Arquitetura" para **"Funcionalidade Completa, Integração Total e Validação"**.

### Principais Marcos Alcançados (Pós-PC3):
1. **Inteligência Artificial Totalmente Funcional (LLaVA via Ollama)**:
   * A recomendação de outfits baseada em VLM passou de conceptual/mock para **produção local real**.
   * Processamento e envio de imagens reais codificadas em Base64 para a IA através do `ImagePreprocessingService`.
2. **Camada de Validação Robusta (Validation Layer - Fase 3/4)**:
   * Implementação de um pipeline de validação em 3 níveis (Existência/Estado das peças, Compatibilidade com a Temperatura/Clima e Cobertura de Camadas).
   * Lógica de tentativa de recuperação (*retry*) com filtros mais rígidos e aviso de erros.
   * Sistema de *fallback* automático para o motor de regras determinístico caso a IA falhe.
3. **Novas Funcionalidades de Negócio**:
   * **Perfil Masculino Totalmente Funcional**: Ajuste e filtragem de estilo adaptados para guarda-roupa masculino.
   * **Gestão de Uso e Métricas (`usage_service.py`)**: Registo de frequência e última utilização das peças para evitar repetições excessivas.
4. **Fecho do Ciclo Frontend-Backend**:
   * O manequim visual do frontend renderiza o outfit por camadas a partir da resposta estruturada da IA.
   * Diálogos interativos de Chat AI e Planeador de Viagens integrados.

---

## 🖥️ Estrutura de Slides Proposta para o PC4

### Slide 1: Capa / Apresentação do Projeto
*   **Título Principal:** My Closet
*   **Subtítulo:** Sistema Inteligente de Gestão de Guarda-Roupa e Recomendação Assistida por IA
*   **Fase:** Ponto de Controlo 4 - Apresentação de Fecho
*   **Autores:** Diogo Viana (29195) & Gonçalo Oliveira (29198)
*   **Orientador:** Professor Doutor Miguel Cruz
*   **Data:** Junho de 2026
*   **Notas do Orador:** "Bom dia a todos. Apresentamos o estado final do projeto My Closet no Ponto de Controlo 4. Conseguimos fechar todo o ciclo de desenvolvimento, integrando a Inteligência Artificial local com um pipeline de validação rigoroso e expandindo as funcionalidades da plataforma."

---

### Slide 2: Agenda da Apresentação
*   **Tópicos:**
    1. Introdução e Objetivos Globais
    2. Progresso face ao PC3 (O que mudou?)
    3. Arquitetura Final e Pipeline de IA
    4. Nova Camada de Validação e Robustez
    5. Funcionalidades Desenvolvidas (Demonstração de Casos Reais)
    6. Resultados de MLOps (MLflow)
    7. Conclusão e Trabalho Futuro
*   **Notas do Orador:** "A nossa apresentação de hoje está dividida em sete partes, focando-nos principalmente nas evoluções operacionais desde o último ponto de controlo, a engenharia por trás do pipeline de validação e a demonstração prática do sistema em funcionamento."

---

### Slide 3: O Salto Tecnológico: PC3 vs PC4
*   **Tabela Comparativa:**
    
    | Dimensão | Estado no PC3 | Estado Final no PC4 |
    | :--- | :--- | :--- |
    | **Motor de IA** | Mock / Preparação para LLaVA | **LLaVA Local Operacional (Ollama)** |
    | **Processamento Visual** | Apenas upload de metadados | **Preprocessamento e Codificação Base64 Real** |
    | **Filtros de Erro** | Aceitação cega da resposta da IA | **Camada de Validação em 3 Níveis + Retries** |
    | **Funcionalidades** | Perfil Unissexo e Base do Canvas | **Perfil Masculino Funcional + Histórico de Uso** |
    | **Infraestrutura** | Estrutura de Routers Básica | **MLflow ativo para monitorização de Prompts** |
*   **Notas do Orador:** "No PC3 tínhamos a fundação pronta e a IA em modo simulado. No PC4, a IA está integrada e funcional localmente com o Ollama, as imagens reais do guarda-roupa são processadas e validadas por um sistema de três camadas para evitar alucinações, e adicionámos regras de negócio reais como o perfil masculino e frequência de desgaste de peças."

---

### Slide 4: Arquitetura Final do Pipeline de IA
*   **Diagrama de Fluxo (Texto Visual):**
    1. **Pedido do Frontend:** Clima Atual + Preferências de Estilo do Utilizador.
    2. **Preparação de Dados (`DataPreparationService`):** Combina dados do Supabase, clima e frequência de uso.
    3. **Pré-processamento de Imagem (`ImagePreprocessingService`):** Valida tamanhos, formatos e converte URLs em Base64.
    4. **Orquestração da IA (`VLMService` / LLaVA):** Envia o prompt de engenharia e as imagens para a IA local.
    5. **Camada de Validação e Parser:** Garante que a IA não inventou peças e que estas se adequam ao clima.
    6. **Resposta Estruturada:** Renderização visual no manequim do frontend.
*   **Notas do Orador:** "Desenvolvemos um pipeline modular em Python com FastAPI. Quando o utilizador pede uma recomendação, os metadados e as imagens das peças são carregados do Supabase, convertidos em Base64, e enviados para o LLaVA. A resposta é então parseada e validada."

---

### Slide 5: Camada de Validação (O Escudo Contra Alucinações)
*   **Pontos-Chave:**
    *   **Nível 1: Validação de Existência e Estado**
        *   Garante que o ID da peça recomendado existe no guarda-roupa.
        *   Bloqueia peças marcadas como "sujas" ou "danificadas".
    *   **Nível 2: Compatibilidade Climática e Térmica**
        *   Verifica se a peça se adequa à temperatura atual e condições meteorológicas (ex: casaco impermeável para chuva).
    *   **Nível 3: Cobertura de Camadas**
        *   Valida a completude do outfit (presença de camada base e calçado).
*   **Notas do Orador:** "Um dos maiores desafios com modelos VLM são as alucinações. Criámos uma Camada de Validação em três níveis. Se a IA sugerir uma peça inexistente ou que esteja suja para lavar, o sistema deteta o erro imediatamente."

---

### Slide 6: Lógica de Recuperação (Retry) e Fallback
*   **Fluxo de Recuperação:**
    *   **Primeira Tentativa:** Execução do LLaVA com contexto aberto.
    *   **Falha na Validação?** O sistema faz um *Retry* imediato com filtros mais apertados e injeta os erros anteriores no prompt da IA (ex: *"Não uses a peça X porque está suja"*).
    *   **Falha persistente?** *Fallback* transparente para o motor de regras determinístico (Phase 1).
    *   **Metadado `model_used`**: Retornado à interface para transparência operacional (`"llava"`, `"llava_fallback"` ou `"rule_based"`).
*   **Notas do Orador:** "Se a validação falhar na primeira ronda, não desistimos. O backend aplica filtros mais estritos ao guarda-roupa e repete o pedido à IA com indicações corretivas. Se mesmo assim falhar, o utilizador recebe uma sugestão baseada no nosso motor de regras original, garantindo que a aplicação nunca falha."

---

### Slide 7: Nova Funcionalidade: Perfil Masculino Completo
*   **Detalhes:**
    *   Filtros de categorização adaptados a padrões e estilos masculinos.
    *   Ajuste da IA nas regras de recomendação (adequação de conjuntos e ocasiões).
    *   Manutenção de consistência visual no manequim de sobreposição.
*   **Notas do Orador:** "Além do motor de inteligência artificial, fechámos os requisitos de negócio com o desenvolvimento do perfil masculino funcional. Agora, as recomendações estéticas e a filtragem do catálogo adaptam-se dinamicamente conforme o género e as preferências declaradas no perfil."

---

### Slide 8: Caso Prático - Demonstração de Fluxo Real
*   **Exemplo de Execução:**
    *   **Input do Clima:** 20°C, Sol, Vento Ligeiro.
    *   **Preferência:** Estilo Casual.
    *   **Output da IA (LLaVA):**
        *   *Peças:* Camisola de Algodão Branca (ID `base_001`), Calças Chino Pretas (ID `outer_003`), Ténis Brancos (ID `outer_004`).
        *   *Raciocínio Gerado:* "Para um dia ameno de 20°C e sol, uma camisola de algodão garante conforto térmico. Os tons neutros de preto e branco complementam-se num visual casual e limpo."
    *   **Validação:** Aprovado em todos os níveis. `model_used` = `"llava"`.
*   **Notas do Orador:** "Aqui vemos um caso real de recomendação. A IA não só escolheu peças válidas que estavam disponíveis e limpas, como gerou uma justificação em linguagem natural coerente e correta sobre a escolha térmica e cromática das peças."

---

### Slide 9: MLOps com MLflow (Monitorização do Sistema)
*   **Funcionalidades Integradas:**
    *   Registo de versões de Prompts utilizadas ao longo dos testes.
    *   Mapeamento do tempo de resposta e latência do LLaVA local.
    *   Taxa de sucesso das recomendações (rácio de validações diretas vs retries).
*   **Notas do Orador:** "Usámos o MLflow para monitorizar o desempenho da IA. Isso permite-nos acompanhar a taxa de sucesso das respostas geradas pelo LLaVA local, analisar os tempos de inferência e ajustar a engenharia de prompts de forma científica."

---

### Slide 10: Conclusão e Balanço do Projeto
*   **Pontos Finais:**
    *   **Sucesso do Desenvolvimento:** Transição concluída de um catálogo simples para um ecossistema inteligente, funcional e interativo.
    *   **Robustez e Privacidade:** Inferência local com Ollama protege os dados do utilizador e elimina custos de APIs externas.
    *   **Qualidade do Código:** Cobertura de testes unitários (`backend/services/__tests__/`) para garantir a fiabilidade dos parsers e serviços.
*   **Notas do Orador:** "Concluindo, o My Closet App atingiu o nível de maturidade exigido para a entrega final. Unimos engenharia de software tradicional a técnicas modernas de Inteligência Artificial e MLOps, garantindo uma aplicação robusta, rápida e totalmente focada na privacidade do utilizador."

---

### Slide 11: Perguntas & Respostas
*   **Texto:** Agradecemos a atenção. Estamos disponíveis para perguntas.
*   **Notas do Orador:** "Muito obrigado a todos pela vossa atenção. Estamos agora abertos a quaisquer perguntas ou comentários sobre o My Closet App."
