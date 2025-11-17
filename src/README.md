# My Closet - Gestão Inteligente de Inventário Têxtil

Uma plataforma completa para gestão de inventário têxtil pessoal e institucional, focada na caracterização técnica das peças (camadas, temperatura, materiais) e sugestão de uso.

## Funcionalidades Principais

### 1. **Autenticação de Utilizadores**
- Login/Signup com email e password
- Modo Visitante para acesso a dados públicos
- Sessão persistente com Supabase Auth

### 2. **Dashboard Inteligente**
- Widget meteorológico com temperatura, humidade e condições
- **Sugestão do Dia**: Sistema de 3 camadas baseado na temperatura
  - Camada 1: Base (contacto com pele)
  - Camada 2: Isolamento térmico
  - Camada 3: Proteção contra elementos
- Resumo do inventário com estatísticas

### 3. **Inventário Completo**
- Galeria Masonry Grid responsiva
- **Filtros avançados**:
  - Tipo de roupa (Casaco, Camisola, T-shirt, etc.)
  - Camada (1, 2, 3)
  - Estação (Inverno, Outono, Primavera, Verão)
  - Estado (Limpo/Sujo)
- Pesquisa por nome

### 4. **Catalogação em 3 Steps**
**Step 1 - Identificação Visual:**
- Upload de foto com armazenamento no Supabase Storage
- Nome, marca e tamanho da peça

**Step 2 - Classificação Têxtil:**
- Tipo de roupa
- Sistema de camadas (1, 2, 3)
- Materiais (tags múltiplos)
- Peso em gramas

**Step 3 - Condições de Uso:**
- Range de temperatura (slider -20°C a 40°C)
- Resistências: Impermeável, Corta-vento
- Estações recomendadas

### 5. **Detalhe da Peça**
- Visualização completa de todas as características
- Toggle para marcar como "Está a lavar"
- Favoritos
- Edição e remoção
- Guia de utilização inteligente

### 6. **Pesquisa por Imagem**
- Upload de foto para verificar peças semelhantes
- Percentagem de compatibilidade (Match %)
- Evita compras duplicadas

## Tecnologias Utilizadas

- **Frontend**: React, TypeScript, Tailwind CSS
- **UI Components**: shadcn/ui
- **Icons**: lucide-react
- **Layout**: react-responsive-masonry
- **Backend**: Supabase (Auth, Storage, Edge Functions)
- **Database**: Supabase KV Store
- **Server**: Hono (Deno Edge Function)

## Design System

### Cores
- **Primária**: Emerald 700 (`#047857`) - Verde floresta
- **Secundária**: Amber 600 (`#d97706`) - Para alertas e acentos
- **Neutras**: Slate/Stone para fundos e textos

### Tipografia
- Sans Serif limpa para fácil leitura de dados técnicos

## Arquitetura Backend

```
Frontend -> Supabase Edge Function (Hono Server) -> KV Store + Storage
```

### Endpoints da API

- `POST /make-server-1d4585bc/signup` - Criar novo utilizador
- `GET /make-server-1d4585bc/items` - Obter inventário do utilizador
- `POST /make-server-1d4585bc/items` - Adicionar nova peça
- `PUT /make-server-1d4585bc/items/:id` - Atualizar peça
- `DELETE /make-server-1d4585bc/items/:id` - Apagar peça
- `POST /make-server-1d4585bc/upload-image` - Upload de imagem

### Storage
- Bucket privado: `make-1d4585bc-closet-images`
- Signed URLs com expiração de 1 ano
- Limite de tamanho: 5MB por imagem

## Como Usar

### Para Utilizadores Pessoais:
1. Criar conta no separador "Cliente / Utilizador Pessoal"
2. Fazer login
3. Adicionar peças usando o botão flutuante "+"
4. Consultar sugestões diárias no Dashboard
5. Gerir inventário com filtros

### Para Investigadores:
1. Aceder como "Investigador / Visitante"
2. Explorar base de dados pública
3. Ver tendências e estatísticas

## Estrutura de Dados

### ClothingItem
```typescript
{
  id: string;
  name: string;
  brand: string;
  size: string;
  type: string;
  layer: 1 | 2 | 3;
  materials: string[];
  weight: number;
  tempMin: number;
  tempMax: number;
  waterproof: boolean;
  windproof: boolean;
  seasons: string[];
  image: string;
  status: 'clean' | 'dirty';
  favorite: boolean;
}
```

## Segurança

- Autenticação via Supabase Auth
- Access tokens JWT para autorização
- Service Role Key apenas no backend
- Buckets privados com signed URLs
- Dados isolados por utilizador

## Próximos Passos Sugeridos

- [ ] Integração com API meteorológica real (OpenWeatherMap)
- [ ] Machine Learning para pesquisa por imagem
- [ ] Partilha de outfits com amigos
- [ ] Estatísticas de uso de peças
- [ ] Lembretes de lavandaria
- [ ] Exportação de inventário (PDF/Excel)
- [ ] App mobile com React Native

---

**Nota**: Esta aplicação é um protótipo desenvolvido no Figma Make. Para produção, considere implementar validações adicionais, testes e otimizações de performance.
