# CHANGELOG — Bipinho

Todas as mudanças notáveis deste projeto são documentadas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

---

## [1.5.0] — 2026-10-27

### Etapa 5 — Manutenção e Distribuição

#### Adicionado
- **Script `atualizar.bat`**:
  - Encerra qualquer processo em execução na porta 8000.
  - Sincroniza com o repositório GitHub via `git pull origin main`.
  - Atualiza as dependências do `requirements.txt`.
  - Preserva 100% intactos os vídeos e imagens (`media/`) e o banco de dados (`data/`).
  - Reinicia o servidor automaticamente com mensagens claras em português.
- **Empacotamento Opcional com PyInstaller**:
  - Arquivo de especificação `bipinho.spec` que compila a aplicação FastAPI e os arquivos estáticos.
  - Exclui explicitamente `data/` e `media/` do pacote `.exe`, garantindo que novos desenhos e o banco SQLite sejam gravados de forma persistente no disco do usuário ao lado do executável.
  - Script `empacotar.py` e inicializador `empacotar.bat` para geração do executável com 1 clique.
- **Página "Sobre / Versão" no Painel Administrativo**:
  - Nova aba "ℹ️ Sobre / Versão" exibindo a versão `1.5.0` do Bipinho, status das 5 etapas concluídas, atalhos de manutenção e leitor integrado do `CHANGELOG.md`.
  - Endpoint `GET /api/admin/about` retornando versão, etapas concluídas e texto do changelog.
- **Checklist Físico de Verificação na TV Real (`CHECKLIST_TV.md`)**:
  - Guia de teste prático cobrindo reconexão, wake lock, bipe durante vídeo, limite diário, tempo assistido, impressão e backup.
- **Script Utilitário `resetar_senha.py` e `resetar_senha.bat`**:
  - Permite redefinir a senha de administrador diretamente pelo terminal ou com duplo-clique.

#### Testes novos
- `tests/test_etapa5.py` — 6 testes cobrindo endpoint `/api/admin/about`, integridade do `atualizar.bat`, arquivo de especificação do PyInstaller `bipinho.spec` (com exclusão de dados e mídias), script `empacotar.py`, script `resetar_senha.py` e existência do checklist de TV.

---

## [1.4.0] — 2026-10-27

### Etapa 4 — Experiência da Criança

#### Adicionado
- **Categorias com Cores Próprias** (`app/database.py`):
  - Tabela `categories` com 5 categorias padrão: *Animais* (`#10b981`), *Músicas* (`#f59e0b`), *Histórias* (`#3b82f6`), *Educativos* (`#8b5cf6`) e *Geral* (`#64748b`).
  - Cada desenho possui sua categoria, exibida com crachá colorido no painel de administração e com faixa no topo dos cartões impressos.
  - Endpoint `GET /api/admin/categories` e suporte nos formulários de cadastro e edição de desenhos.
- **Cartões de Contorno para Colorir (P&B)** (`app/services/outline_service.py`):
  - Algoritmo de processamento de imagem com detecção de bordas (Sobel / `FIND_EDGES` via Pillow) que transforma imagens e miniaturas de vídeos em desenhos limpos de linhas em preto e branco.
  - Rota `/admin/colorir/{item_id}` com folha A4 pronta para impressão em preto e branco, contendo o desenho para colorir, título, código de barras Code128 e instruções lúdicas para a criança bipar na TV após pintar.
  - Botão de acesso rápido `🖍️ Colorir` em cada cartão de desenho no painel administrativo.
- **Modos de Impressão Flexíveis e Caça ao Tesouro** (`app/templates/print_cards.html`):
  - Seletor de tamanho na folha A4:
    - *Padrão (6 por folha)*: Para montar a pastinha tradicional de cartões.
    - *Grandes (2 por folha)*: Cartões maiores para mãos pequenas e maior visibilidade.
    - *Caça ao Tesouro (1 por folha)*: Cartão gigante com borda temática especial para os pais esconderem pela casa e a criança procurar para bipar.
  - Opção *Agrupar por Categoria* para ordenar os cartões na folha por categoria.
  - Faixa colorida da categoria no topo de cada cartão impresso.
- **Mascote Bipinho Animado na Tela de Espera** (`app/templates/child.html`, `static/css/child.css`):
  - Mascote leitorzinho em SVG e CSS puro (sem dependências ou imagens pesadas):
    - Olhinhos que piscam suavemente a cada 4 segundos (`@keyframes mascotBlink`).
    - Bracinho que acena suavemente (`@keyframes mascotWave`).
    - Linha de laser vermelho sutil pulsando no visor.
    - Reação comemorativa ao receber um bipe válido: pulo de alegria (`mascotCheerJump`), aceno rápido e efeito sonoro alegre.
  - Respeita a configuração de som da administração e a opção de desativar o mascote (`mascot_enabled`).
- **Interface 10-foot UI pura**:
  - Zero botões clicáveis na tela da criança, foco automático constante no leitor e fontes legíveis de longe na TV.

#### Testes novos
- `tests/test_etapa4.py` — 7 testes cobrindo categorias no banco e API, CRUD de itens com categoria, gerador de contorno P&B para colorir, rota da folha de colorir, recursos da folha de impressão (tamanhos 1/2/6 e agrupamento), mascote animado e desafios de movimento na pausa.

---

## [1.3.0] — 2026-10-27

### Etapa 3 — Controle dos Pais

#### Adicionado
- **Agenda de Uso e Limites Configuráveis** (`app/services/schedule_service.py`):
  - Limite máximo de sessões permitidas por dia (com contagem automática de sessões concluídas).
  - Horário permitido de início e encerramento (ex: 07:00 às 21:00).
  - Dias da semana permitidos (chips interativos de Seg a Dom).
  - Bloqueio manual da TV direto pelo painel de controle.
- **Tela "O Bipinho está dormindo..."** (`child.html` & `child.css`):
  - Exibida quando a TV é aberta fora do horário ou dias permitidos, ao atingir o limite diário de sessões ou sob bloqueio manual.
  - Mascote sonolento animado em CSS puro (sem bibliotecas externas) com mensagem amigável explicando o motivo.
- **Liberação Excepcional pela Chave dos Pais**:
  - Bipar o cartão secreto dos pais (`parent_unlock_code`) fora dos horários permitidos desbloqueia a TV excepcionalmente para aquela sessão, acordando o Bipinho na hora.
- **Painel ao Vivo Responsivo para Celular (📺)** (`admin.html` & `admin.js`):
  - Exibe em tempo real: desenho em reprodução, estrelas acumuladas, tempo total assistido, estado da pausa e da agenda.
  - Botões de ação imediata: "▶️ Encerrar Pausa Agora", "🔒 Bloquear TV", "🔓 Liberar TV" e "🔄 Reiniciar Sessão".
  - Layout adaptado para smartphones e tablets via CSS grid flexível.
- **Histórico Semanal com Gráfico em SVG Puro (📈)**:
  - Tempo total de tela por dia e número de sessões nos últimos 7 dias.
  - Gráfico de barras desenhado com SVG/CSS inline sem dependências ou CDNs externas.
  - Tabela detalhada com data, sessões, tempo de tela e desenhos mais assistidos.
  - Armazenamento dedicado nas tabelas SQLite `daily_sessions` e `view_history`.
- **Importação em Lote de Pastas do Servidor (📂)**:
  - Permite informar uma pasta do PC contendo vídeos e imagens.
  - O sistema lê todos os arquivos, gera títulos amigáveis a partir do nome do arquivo, atribui códigos sequenciais Code128, converte formatos não compatíveis com FFmpeg e gera miniaturas.
  - Relatório detalhado de itens cadastrados com avisos e eventuais falhas.
- **Diagnóstico e Alertas no Cadastro de Vídeos**:
  - Detecção com `ffprobe` de duração (alerta se > 30 min) e resolução (alerta se 4K / > 1080p).
  - Sugestão e conversão automática com FFmpeg para MP4 (H.264/AAC).
- **Separação da Chave dos Pais na Impressão de Cartões**:
  - A folha A4 separa a "Chave dos Pais (Liberar Pausa)" em uma página própria com borda vermelha e tarja destacada: *"⚠️ NÃO COLOCAR NA PASTINHA DA CRIANÇA! Guarde em local reservado aos adultos"*.
  - O cartão "Desenho Surpresa!" permanece junto aos cartões normais para recorte na pastinha da criança.
- **Lista de Desafios de Movimento**:
  - 15 desafios pré-cadastrados no banco de dados (ex: "Dê 10 pulinhos!", "Gire como um bailarino!").
  - Editor completo na aba de Controle dos Pais para adicionar, ativar, desativar ou remover sugestões.
  - Exibição de sugestão sorteada na tela de pausa "Hora de colorir!".

#### Testes novos
- `tests/test_etapa3.py` — 10 testes cobrindo: agenda desativada, bloqueio manual da TV, restrição de horário, restrição de dias da semana, tela de bloqueio e desbloqueio excepcional pela chave dos pais, 15 desafios padrão e API, APIs do painel ao vivo, rastreamento de histórico diário/semanal, importação em lote e separação da chave dos pais na folha de impressão.

---

## [1.2.0] — 2026-10-27

### Etapa 2 — Confiabilidade na TV

#### Adicionado
- **Screen Wake Lock API**: Impede que a tela da TV apague enquanto o Bipinho está aberto no navegador. Inclui fallback com vídeo mudo invisível em loop para navegadores antigos de Android TV (`static/js/child.js`).
- **Reconexão automática ao servidor**: Ao perder a conexão SSE (ex: servidor reiniciado), a TV exibe o overlay amigável "Bipinho já volta! / Reconectando..." e tenta reconectar automaticamente a cada 3 segundos. Ao reconectar, sincroniza o estado completo da sessão (estrelas, pausa) sem recarregar a página.
- **Comportamento de bipe durante vídeo (configurável)**:
  - `interrupt` (padrão): Interrompe o vídeo atual e inicia o novo desenho imediatamente.
  - `ignore`: Ignora o bipe até o vídeo atual terminar, exibindo aviso amigável na tela da TV.
- **Novo modo de contagem "Por tempo assistido"**: A pausa "Hora de colorir!" começa após X minutos de reprodução acumulada (configurável, padrão: 15 min). O tempo é reportado ao servidor a cada 5 segundos enquanto o vídeo está em reprodução.
- **Backup e Restauração** (`app/services/backup_service.py`):
  - Botão "📥 Baixar Backup (.zip)" exporta banco SQLite + todas as mídias e miniaturas em um clique.
  - Botão "📤 Restaurar Backup" importa o zip com validação de integridade e proteção contra path traversal.
  - Rotas protegidas por autenticação: `GET /api/admin/backup/export` e `POST /api/admin/backup/restore`.
- **Nova coluna `watched_seconds`**: Migração automática na tabela `session_state` do banco para rastrear tempo assistido acumulado.

#### Testes novos
- `tests/test_etapa2.py` — 9 testes cobrindo: comportamento `interrupt` e `ignore`, reporte de tempo, acionamento de pausa, export de backup válido, restore via API, rejeição de ZIP inválido, overlay de reconexão e novos campos em `/api/session/status`.

---

## [1.1.0] — 2026-10-27

### Etapa 1 — Segurança e Higiene do Repositório

#### Adicionado
- **Hash de senha com sal (PBKDF2-HMAC-SHA256)**: 100.000 iterações com salt individual de 16 bytes.
- **Troca de senha obrigatória no primeiro login**: Redirecionamento forçado para `/admin/trocar-senha-obrigatoria`.
- **Proteção contra força bruta (Rate Limiting por IP)**: Bloqueio temporário por IP após 5 tentativas incorretas.
- **Restrição de acesso ao /admin**: Opção `localhost_only` para bloquear acesso externo à administração.
- **Aba de Diagnóstico do Sistema (🩺)**: Verificação de saúde, disco, integridade SQLite, FFmpeg e energia.
- **Alerta de FFmpeg ausente**: Rejeição clara de uploads que dependem de conversão.
- **Migração automática do banco**: Migração automática de senhas plaintext antigas para PBKDF2.

#### Testes novos
- `tests/test_etapa1.py` — 6 testes cobrindo hash/salt, primeiro login, rate limiting, restrição por IP, endpoint de diagnósticos e detecção de FFmpeg ausente.

---

## [1.0.0] — 2026-10-20

### Lançamento Inicial
- Interface da criança (tela cheia, 10-foot UI, sem botões).
- Leitura de códigos de barra via teclado HID.
- Sistema de estrelas e pausa visual "Hora de colorir!".
- Streaming de vídeos com suporte a Range RFC 7233.
- Geração de código de barras Code128 em SVG inline.
- Folha de impressão A4 com linhas de corte para pastinha.
