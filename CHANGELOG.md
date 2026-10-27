# CHANGELOG — Bipinho

Todas as mudanças notáveis deste projeto são documentadas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

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

## [1.1.0] — 2026-10-27

### Etapa 1 — Segurança e Higiene do Repositório

#### Adicionado
- **Hash de senha com sal (PBKDF2-HMAC-SHA256)**: A senha do administrador nunca mais é armazenada em texto puro. O algoritmo usa 100.000 iterações de PBKDF2 com salt aleatório de 16 bytes (`app/services/auth_service.py`).
- **Troca de senha obrigatória no primeiro login**: O sistema detecta o uso contínuo da senha padrão e força a criação de uma senha pessoal antes de liberar o acesso ao painel (`app/templates/force_password.html`).
- **Proteção contra força bruta (Rate Limiting por IP)**: Após N tentativas de login incorretas (padrão: 5), o IP fica bloqueado temporariamente por X minutos (padrão: 15). Configurável na aba de Configurações Gerais (`app/services/rate_limiter.py`).
- **Restrição de acesso ao /admin**: Nova opção na admin para restringir o painel exclusivamente ao localhost (PC servidor), bloqueando TVs, celulares e tablets com HTTP 403 (`admin_access_restriction`).
- **Aba de Diagnóstico do Sistema (🩺)**: Exibe em tempo real: versão do Bipinho, espaço livre em disco, integridade do banco SQLite (`PRAGMA integrity_check`), caminho e versão do FFmpeg e alerta de suspensão de energia do Windows (`app/services/diagnostic_service.py`).
- **Alerta de FFmpeg ausente**: Ao tentar cadastrar vídeos que requerem conversão sem o FFmpeg instalado, o sistema rejeita o upload com mensagem clara e instruções de instalação.
- **Migração automática do banco**: Ao iniciar, o `init_db()` detecta e migra a senha plaintext legada para hash PBKDF2, sem intervenção manual.

#### Testes novos
- `tests/test_etapa1.py` — 6 testes cobrindo hash/salt, primeiro login, rate limiting, restrição por IP, endpoint de diagnósticos e detecção de FFmpeg ausente.

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
- **Seção de Backup & Restauração no painel admin**: Interface completa com export, import e feedback de sucesso/erro.
- **Endereço para o novo endpoint**: `POST /api/session/report-watch-time` — reporta segundos assistidos e verifica o limite do modo por tempo.

#### Modificado
- `static/css/child.css`: Adicionados estilos do overlay de reconexão (`.connection-toast-layer`) com animação pulsante.
- `static/js/child.js`: Wake Lock, reconexão robusta de SSE, envio de `is_video_playing` no scan, timer de reporte de tempo assistido.
- `static/js/admin.js`: Carregamento e salvamento das novas configurações (`video_scan_behavior`, `watch_time_limit_minutes`) e listener do formulário de restauração de backup.
- `app/templates/admin.html`: Nova opção "Por tempo assistido" nos modos de contagem, campo de limite de tempo, seletor de comportamento de bipe durante vídeo, seção de Backup & Restauração.

#### Testes novos
- `tests/test_etapa2.py` — 9 testes cobrindo: comportamento `interrupt` e `ignore` de bipe durante vídeo, reporte de tempo sem pausa, reporte de tempo que aciona pausa, export de backup válido, restore via API, rejeição de ZIP inválido, overlay de reconexão no HTML da TV e campos novos em `/api/session/status`.

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

## [1.0.0] — 2026-10-20

### Lançamento Inicial

- Interface da criança (tela cheia, 10-foot UI, sem botões)
- Leitor de código de barras como teclado (USB, 2.4G, Bluetooth)
- Sistema de estrelas e pausa "Hora de colorir!"
- Painel administrativo com CRUD de desenhos, geração de codes Code128 e folha A4 de impressão
- Streaming de vídeo com suporte a Range RFC 7233
- Código Surpresa (desenho aleatório) e Código dos Pais (liberar pausa)
- Configuração completa de perfil de leitor (debounce, terminador, prefixo/sufixo)
- Estatísticas de favoritos
- Server-Sent Events para sincronização em tempo real entre admin e TV
- `iniciar_bipinho.bat`, `iniciar_em_segundo_plano.vbs`, `instalar_inicializacao_windows.bat`
- Suíte de 15 testes automatizados
- README completo em português com instalação, firewall, TV e checklist de leitor
