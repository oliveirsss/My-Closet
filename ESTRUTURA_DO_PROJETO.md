```markdown
# Estrutura do Projeto — My Closet App

Este ficheiro apresenta a estrutura actual do repositório e uma árvore detalhada dos ficheiros detectados.

> Observação: caminhos e conteúdos baseados no workspace actual (nov. 2025).

## Visão geral (top-level)

- `.gitignore`
- `.npmrc`
- `package-lock.json`
- `package.json`
- `vite.config.ts`
- `index.html`
- `README.md`
- `ESTRUTURA_DO_PROJETO.md` (este ficheiro)
- `.idea/` (config do IDE - contém ficheiros de projecto)


## Árvore completa detectada (resumida)

Note: os caminhos são relativos à raiz do projecto (`My Closet App`).

### `backend/`

- `backend/main.py`
- `backend/__pycache__/main.cpython-313.pyc`

### `src/` (frontend)

- `src/App.tsx`
- `src/main.tsx`
- `src/index.css`
- `src/Attributions.md`
- `src/README.md`

#### `src/styles/`

- `src/styles/globals.css`

#### `src/guidelines/`

- `src/guidelines/Guidelines.md`

#### `src/supabase/functions/server/`

- `src/supabase/functions/server/index.tsx`
- `src/supabase/functions/server/kv_store.tsx`

#### `src/utils/`

- `src/utils/api.ts`
- `src/utils/supabase.ts`
- `src/utils/supabase/info.tsx`

#### `src/components/`

- `src/components/AddItemDialog.tsx`
- `src/components/LoginScreen.tsx`
- `src/components/ItemDetail.tsx`
- `src/components/Inventory.tsx`
- `src/components/ImageSearch.tsx`
- `src/components/Dashboard.tsx`

##### `src/components/figma/`

- `src/components/figma/ImageWithFallback.tsx`

##### `src/components/ui/` (componentes reutilizáveis)

- `src/components/ui/accordion.tsx`
- `src/components/ui/alert-dialog.tsx`
- `src/components/ui/alert.tsx`
- `src/components/ui/aspect-ratio.tsx`
- `src/components/ui/avatar.tsx`
- `src/components/ui/badge.tsx`
- `src/components/ui/breadcrumb.tsx`
- `src/components/ui/button.tsx`
- `src/components/ui/calendar.tsx`
- `src/components/ui/card.tsx`
- `src/components/ui/carousel.tsx`
- `src/components/ui/chart.tsx`
- `src/components/ui/checkbox.tsx`
- `src/components/ui/collapsible.tsx`
- `src/components/ui/command.tsx`
- `src/components/ui/context-menu.tsx`
- `src/components/ui/dialog.tsx`
- `src/components/ui/drawer.tsx`
- `src/components/ui/dropdown-menu.tsx`
- `src/components/ui/form.tsx`
- `src/components/ui/hover-card.tsx`
- `src/components/ui/input-otp.tsx`
- `src/components/ui/input.tsx`
- `src/components/ui/label.tsx`
- `src/components/ui/menubar.tsx`
- `src/components/ui/navigation-menu.tsx`
- `src/components/ui/pagination.tsx`
- `src/components/ui/popover.tsx`
- `src/components/ui/progress.tsx`
- `src/components/ui/radio-group.tsx`
- `src/components/ui/resizable.tsx`
- `src/components/ui/scroll-area.tsx`
- `src/components/ui/select.tsx`
- `src/components/ui/separator.tsx`
- `src/components/ui/sheet.tsx`
- `src/components/ui/sidebar.tsx`
- `src/components/ui/skeleton.tsx`
- `src/components/ui/slider.tsx`
- `src/components/ui/sonner.tsx`
- `src/components/ui/switch.tsx`
- `src/components/ui/table.tsx`
- `src/components/ui/tabs.tsx`
- `src/components/ui/textarea.tsx`
- `src/components/ui/toggle.tsx`
- `src/components/ui/toggle-group.tsx`
- `src/components/ui/tooltip.tsx`
- `src/components/ui/use-mobile.ts`
- `src/components/ui/utils.ts`


## Ficheiros de IDE / config

- `.idea/My Closet App.iml`
- `.idea/vcs.xml`
- `.idea/modules.xml`
- `.idea/misc.xml`
- `.idea/.gitignore`
- `.idea/inspectionProfiles/profiles_settings.xml`


## Notas rápidas

- O backend principal é `backend/main.py` (FastAPI). Verificar `SUPABASE_URL` e `SUPABASE_KEY` no `.env`.
- O frontend usa `src/` com `App.tsx` como ponto central e muitos componentes na pasta `src/components` e `src/components/ui`.
- `src/utils/api.ts` aponta para `http://127.0.0.1:8000` por defeito — ajustar para `import.meta.env.VITE_API_BASE` se necessário.
- Há ficheiros gerados pelo Python em `backend/__pycache__` e ficheiros do IDE em `.idea/`.


---

Se quiser, atualizo este ficheiro para incluir também o conteúdo resumido de cada ficheiro (ex.: cabeçalhos de `backend/main.py` e `src/App.tsx`) ou gerar um `.env.example` e `requirements.txt`.
```
# Estrutura do Projeto — My Closet App

Este ficheiro apresenta a estrutura atual do repositório e uma breve descrição dos principais ficheiros/pastas.

> Observação: caminhos e conteúdos baseados no workspace atual (nov. 2025).

## Visão geral (top-level)

- `index.html` — Entrada HTML da aplicação.
- `package.json` — Dependências e scripts do frontend.
- `README.md` — Informação geral e instruções mínimas.
- `vite.config.ts` — Configuração do Vite (aliases, porta, build).
- `backend/` — Código do backend (FastAPI + integração Supabase).
- `src/` — Código frontend (React + TypeScript).


## `backend/`

- `main.py` — Servidor FastAPI com endpoints:
  - `GET /health`
  - CRUD `/items` (GET, POST, PUT, DELETE)
  - `POST /upload-image` (upload para Supabase Storage)
  - `POST /signup` (signup via Supabase)

- `__pycache__/` — caches do Python.


## `src/` (frontend)

- `App.tsx` — Componente raíz; controla navegação, sessão e chamadas API.
- `main.tsx` — Entrypoint React (`createRoot`).
- `index.css` — Estilos globais (importado em `main.tsx`).
- `README.md` — Documentação local do frontend.
- `Attributions.md` — Atribuições/licenças (se aplicável).

### `src/components/`
Componentes de UI e telas principais:

- `AddItemDialog.tsx` — Dialog para adicionar peça.
- `Dashboard.tsx` — Tela do dashboard (widget meteorológico, sugestão de outfit).
- `ImageSearch.tsx` — Pesquisa por imagem.
- `Inventory.tsx` — Lista/masonry do inventário.
- `ItemDetail.tsx` — Detalhes da peça, editar/apagar.
- `LoginScreen.tsx` — Tela de login / signup / visitante.

Subpastas:
- `figma/`
  - `ImageWithFallback.tsx` — Helper para imagens com fallback.

- `ui/` — Biblioteca de componentes reutilizáveis (design system). Exemplos de ficheiros:
  - `accordion.tsx`, `alert-dialog.tsx`, `alert.tsx`, `aspect-ratio.tsx`, `avatar.tsx`, `badge.tsx`, `breadcrumb.tsx`, `button.tsx`, `calendar.tsx`, `card.tsx`, `carousel.tsx`, `chart.tsx`, `checkbox.tsx`, `collapsible.tsx`, `command.tsx`, `context-menu.tsx`, `dialog.tsx`, `drawer.tsx`, `dropdown-menu.tsx`, `form.tsx`, `hover-card.tsx`, `input-otp.tsx`, `input.tsx`, `label.tsx`, `menubar.tsx`, `navigation-menu.tsx`, `pagination.tsx`, `popover.tsx`, `progress.tsx`, `radio-group.tsx`, `resizable.tsx`, `scroll-area.tsx`, `select.tsx`, `separator.tsx`, `sheet.tsx`, `sidebar.tsx`, `skeleton.tsx`, `slider.tsx`, `sonner.tsx`, `switch.tsx`, `table.tsx`, `tabs.tsx`, `textarea.tsx`, `toggle-group.tsx`, `toggle.tsx`, `tooltip.tsx`, `use-mobile.ts`, `utils.ts`

- `guidelines/`
  - `Guidelines.md` — Diretrizes de design / uso dos componentes.

- `styles/`
  - `globals.css` — Variáveis/estilos globais adicionais.

- `supabase/`
  - `functions/`
    - `server/`
      - `index.tsx`
      - `kv_store.tsx`

### `src/utils/`
- `api.ts` — Wrapper das chamadas à API backend (`API_BASE = http://127.0.0.1:8000` no código atual), gestão do `accessToken` em memória.
- `supabase.ts` — Cria instância do cliente Supabase para o frontend usando `projectId` e `publicAnonKey` de `src/supabase/info`.
- `supabase/`:
  - `info.tsx` — Valores do `projectId` e `publicAnonKey` (variáveis de configuração pública).


## Dependências principais (ver `package.json`)
- React 18, Vite, plugin React SWC
- Supabase (`@supabase/supabase-js`), Radix UI packages, `lucide-react`, `react-hook-form`, `recharts`, `sonner`, `embla-carousel-react`, entre outros.

Observações: existem dependências com versão `"*"` e aliases no `vite.config.ts`.


## Variáveis de ambiente esperadas
- `SUPABASE_URL` (backend)
- `SUPABASE_KEY` (backend - privada)
- `VITE_OPENWEATHER_API_KEY` (frontend - OpenWeather)
- `projectId` / `publicAnonKey` (frontend - Supabase public anon key) — atualmente em `src/supabase/info.tsx`


## Pontos de atenção rápidos
- Backend (`main.py`) faz logs com parte/len da `SUPABASE_KEY` — possível risco de exposição de segredos.
- CORS está aberto (`allow_origins=["*"]`) no backend.
- `API_BASE` está hardcoded para dev (`127.0.0.1:8000`).
- Confirmar configuração do Tailwind (classes usadas mas `tailwindcss` não aparece nas deps).


---

Se quiser, posso:
- Adicionar este ficheiro ao repositório (já criado aqui).
- Gerar um `README` de execução local ou um `.env.example` com as variáveis necessárias.
- Fixar dependências com versões estáveis.

Quer que eu crie também um `.env.example` e um `requirements.txt` para o backend agora?