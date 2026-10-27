# 📺 Bipinho

O **Bipinho** é um sistema completo, pronto para rodar, criado para incentivar crianças a se movimentarem enquanto assistem a seus desenhos favoritos. Em vez de usar controles remotos ou telas sensíveis ao toque, a criança escolhe o desenho bipando cartões com código de barras usando um leitor óptico.

O sistema funciona **100% offline** (sem internet, sem CDN externa) e roda em rede local: um servidor no PC Windows transmite os desenhos diretamente para o navegador de uma **Android TV**.

---

## 🚀 Estrutura do Projeto

```text
bipinho/
├── app/
│   ├── config.py                 # Configurações, pastas e detecção de IP local
│   ├── database.py               # Banco de dados SQLite, tabelas e consultas
│   ├── main.py                   # Ponto de entrada FastAPI e ciclo de vida
│   ├── seed.py                   # Gerador automático de desenhos de amostra
│   ├── routes/
│   │   ├── admin.py              # Painel administrativo, login, CRUD e configurações
│   │   ├── child.py              # Interface da TV (criança) e API de bipes
│   │   └── media.py              # Streaming de vídeo com suporte a Range (RFC 7233)
│   ├── services/
│   │   ├── auth_service.py       # Hashing seguro de senhas com PBKDF2 e salt
│   │   ├── barcode_service.py    # Geração de códigos de barras Code128 em SVG
│   │   ├── diagnostic_service.py # Verificação de saúde, disco, FFmpeg e energia
│   │   ├── media_service.py      # Conversão de vídeo com ffmpeg e miniaturas
│   │   ├── rate_limiter.py       # Proteção contra ataques de força bruta no login
│   │   └── session_manager.py    # Regras de estrelas, debounce, pausa e eventos SSE
│   └── templates/
│       ├── admin.html            # Dashboard administrativo com abas e diagnóstico
│       ├── child.html            # Interface 10-foot UI para TV em tela cheia
│       ├── force_password.html   # Tela obrigatória de troca de senha no 1º acesso
│       ├── login.html            # Tela de login da administração com lockout
│       └── print_cards.html      # Folha A4 pronta para impressão e recorte
├── data/
│   └── bipinho.db                # Banco de dados SQLite (criado automaticamente)
├── media/
│   ├── uploads/                  # Vídeos e imagens dos desenhos cadastrados
│   └── thumbs/                   # Miniaturas geradas automaticamente
├── static/
│   ├── css/
│   │   ├── admin.css             # Estilos do painel de controle
│   │   └── child.css             # Estilos da TV (fontes grandes, cores vivas, estrelas)
│   ├── js/
│   │   ├── admin.js              # Lógica reativa da admin, diagnóstico e teste
│   │   └── child.js              # Captura do leitor na TV, áudio sintetizado e SSE
│   └── sounds/                   # Efeitos sonoros WAV offline
├── tests/
│   ├── test_bipinho.py           # Suíte de testes de fluxo e regressão (15 testes)
│   └── test_etapa1.py            # Testes de segurança, hashing, rate limit e diagnóstico (6 testes)
├── iniciar_bipinho.bat           # Inicializador rápido (janela aberta)
├── iniciar_em_segundo_plano.vbs  # Inicializador silencioso (sem janela)
├── instalar_inicializacao_windows.bat # Configura início automático com o Windows
├── desinstalar_inicializacao.bat # Remove início automático
├── parar_bipinho.bat             # Encerra o processo do servidor
├── requirements.txt              # Dependências Python
└── README.md                     # Documentação completa
```

---

## 🛠️ 1. Instalação e Como Iniciar

### Pré-requisitos
- **Windows 10 ou 11**
- **Python 3.10 ou superior** instalado (com a opção *"Add Python to PATH"* marcada)
- **FFmpeg**: Essencial para conversão automática de vídeos para o perfil H.264 MP4 suportado pela TV e geração de miniaturas.
  - **Instalação rápida via terminal (PowerShell / Prompt):**
    ```powershell
    winget install Gyan.FFmpeg
    ```
  - **Instalação manual:** Baixe a versão *essentials build* em [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/), descompacte (ex: `C:\ffmpeg`) e adicione o subdiretório `bin` à variável de ambiente `PATH` do Windows.

### Instalação das dependências
Abra o prompt de comando ou PowerShell na pasta do projeto e execute:
```bash
pip install -r requirements.txt
```

### Como iniciar o Bipinho
Você tem duas opções práticas:

1. **Modo Normal (com janela de log):**
   - Dê um duplo-clique no arquivo `iniciar_bipinho.bat`.
   - O servidor exibirá o endereço IP local na tela e estará pronto para conexões.

2. **Modo Silencioso (em segundo plano):**
   - Dê um duplo-clique no arquivo `iniciar_em_segundo_plano.vbs`.
   - O Bipinho rodará silenciosamente no fundo. Para encerrá-lo, use `parar_bipinho.bat`.

3. **Iniciar Junto com o Windows (Recomendado):**
   - Dê um duplo-clique no arquivo `instalar_inicializacao_windows.bat`.
   - Um atalho será criado na pasta `Inicializar` do seu usuário (`shell:startup`). Toda vez que você ligar o computador, o Bipinho já estará rodando e disponível para a TV!

---

## 🔒 2. Liberar a Porta 8000 no Firewall do Windows (Rede Privada)

Para que a TV consiga acessar o computador na mesma rede Wi-Fi/cabo, a porta `8000` precisa ser liberada no Firewall do Windows para conexões privadas.

### Método Rápido (PowerShell como Administrador):
1. Clique com o botão direito no menu Iniciar do Windows e escolha **"Terminal (Admin)"** ou **"PowerShell (Administrador)"**.
2. Cole o comando abaixo e aperte Enter:
```powershell
New-NetFirewallRule -DisplayName "Bipinho Servidor TV" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow -Profile Private
```

### Método Manual (pela interface do Windows):
1. Pressione `Win + R`, digite `wf.msc` e aperte Enter (abre o *Firewall do Windows com Segurança Avançada*).
2. No menu esquerdo, clique em **Regras de Entrada** (*Inbound Rules*).
3. No menu direito, clique em **Nova Regra...** (*New Rule...*).
4. Escolha **Porta** e clique em Avançar.
5. Selecione **TCP** e em *Portas locais específicas* digite: `8000`.
6. Selecione **Permitir a conexão** e clique em Avançar.
7. **Importante:** Marque **apenas a opção "Particular" / "Privada"** (desmarque "Pública" por segurança).
8. Dê o nome: `Bipinho Servidor TV` e clique em Concluir.

---

## 🌐 3. Como Fixar o IP do PC no Roteador (IP Estático / DHCP Reserva)

Para que o endereço não mude sempre que o PC for reiniciado, reserve um IP fixo no roteador da sua casa:

1. **Descubra o MAC Address e o IP atual do seu computador:**
   - Abra o Prompt de Comando (`cmd`) e digite:
     ```cmd
     getmac /v
     ```
   - Anote o endereço físico (MAC Address, exemplo: `00-1A-2B-3C-4D-5E`) do adaptador de rede conectado (Wi-Fi ou Ethernet).

2. **Acesse o painel do seu roteador:**
   - No navegador do PC, acesse o endereço do roteador (geralmente `192.168.1.1` ou `192.168.15.1`).
   - Faça login com as credenciais (que constam na etiqueta embaixo do roteador).

3. **Configure a reserva de DHCP:**
   - Procure pelo menu **Rede Local**, **DHCP** ou **IP Estático / Reserva de Endereço**.
   - Clique em **Adicionar Nova Reserva**.
   - Insira o endereço MAC do seu PC e o IP desejado (exemplo: `192.168.15.8`).
   - Salve e aplique as configurações. Agora o seu PC terá sempre o mesmo IP!

---

## 📺 4. Como Abrir e Usar na Android TV

1. **Ligue a TV e conecte-a na mesma rede Wi-Fi/cabo do computador.**
2. Abra a Google Play Store na Android TV e instale um navegador otimizado para TV:
   - **TV Bro** (⭐ **Mais recomendado:** gratuito, código aberto, com suporte nativo a controle remoto, modo tela cheia real e bloqueador de abas).
   - **JioPages TV** (ótima alternativa com modo tela cheia).
   - **Google Chrome** (se já estiver instalado na TV).
3. Na barra de endereços do navegador da TV, digite:
   ```text
   http://IP-DO-SEU-PC:8000
   ```
   *(O endereço exato com o seu IP é exibido em destaque no cabeçalho do painel de administração em `/admin`, por exemplo: `http://192.168.15.8:8000`).*
4. A tela inicial da criança aparecerá com o título **"Bipinho"** e as estrelas apagadas.

### Dicas caso o navegador da TV não entre em tela cheia perfeita:
- **No TV Bro:** Pressione o botão de menu do controle remoto ou arraste o cursor até a barra superior e ative o ícone de **"Tela Cheia"** (duas setas diagonais). O TV Bro oculta 100% das barras e lembra da configuração nas próximas aberturas.
- **Se a barra de endereços insistir em aparecer:** No TV Bro, vá em *Configurações > Aparência* e marque a opção *"Ocultar barra de ferramentas automaticamente"*.
- **Zoom / Resolução:** Se os elementos parecerem muito grandes ou pequenos na sua TV, use o controle de zoom do próprio navegador da TV (100% costuma ser ideal para telas 4K e Full HD).

---

## 🏷️ 5. Checklist de Teste do Leitor de Código de Barras na TV

O leitor de código de barras funciona exatamente como um teclado USB/Bluetooth: ao ler as barras, ele "digita" os números e caracteres e envia a tecla **Enter** (ou Tab).

### Checklist Passo a Passo:
1. **Teste Físico Básico:**
   - Conecte o cabo USB (ou o dongle sem fio 2.4G) na porta USB da TV. Se for Bluetooth, faça o pareamento nas *Configurações > Controles e Acessórios* da Android TV.
2. **Teste no Campo de Texto:**
   - Abra o YouTube ou o navegador na TV.
   - Clique em qualquer campo de busca de texto para que o cursor pisque.
   - Aponte o leitor para qualquer código de barras de embalagem (ou os cartões impressos do Bipinho).
   - **Resultado esperado:** Os dígitos devem aparecer instantaneamente no campo de busca e a busca deve ser acionada sozinha (porque o leitor envia Enter).
3. **Teste no Bipinho:**
   - Acesse a tela da criança (`/`).
   - Bipe um código válido (ex: `BIP-1001`). O desenho deve iniciar na hora, o som tocar e 1 estrela acender.
4. **Ferramenta de Diagnóstico no PC:**
   - Conecte o leitor no PC e abra o painel `/admin` na aba **"⚡ Testar Leitor"**.
   - Bipe um código. A ferramenta exibirá em tempo real o código bruto, o terminador detectado e a velocidade entre cada caractere em milissegundos, avaliando se a configuração está ótima.

### Dicas por tipo de leitor:
- **🔌 USB com Fio:** É a conexão mais estável. Se nada acontecer ao bipar, desconecte e reconecte o cabo na TV ou teste outra porta USB.
- **📶 Sem Fio 2.4G:** Verifique se o receptor nano-USB está bem encaixado na TV e se as pilhas do leitor estão boas.
- **🔵 Bluetooth:** A maioria dos leitores Bluetooth entra em modo de suspensão após alguns minutos sem uso. Dê um primeiro bipe "no vazio" para acordá-lo antes de bipar o cartão, ou refaça o pareamento nas configurações da TV se perder conexão.

---

## 🖨️ 6. Como Imprimir e Montar a Pastinha da Criança

1. Abra a administração em `http://localhost:8000/admin` (ou pelo IP local). No primeiro acesso à administração, faça login com a senha inicial fornecida na instalação. O sistema exigirá obrigatoriamente a criação de uma senha pessoal nova e segura, armazenada exclusivamente com hash salgado (PBKDF2).
2. Clique no botão **"🖨️ Imprimir Folha A4 de Códigos"** (rota `/admin/imprimir`).
3. Uma folha em layout A4 será montada com:
   - Título **Bipinho** no cabeçalho.
   - Grade de cartões com miniatura do desenho, título, autor e código de barras Code128 em vetor nítido.
   - Linhas tracejadas com guias de tesoura `✂` para corte fácil.
   - **Cartões Especiais:**
     - **Chave dos Pais (Liberar Pausa):** Permite aos pais liberar a TV instantaneamente mesmo durante a "Hora de colorir".
     - **Desenho Surpresa:** Sorteia um desenho aleatório da coleção a cada bipe.
4. Pressione `Ctrl + P` (ou clique em "Imprimir Folha") e imprima em papel sulfite comum ou papel cartão/fotográfico.
5. Recorte os cartões e cole em um caderno, fichário ou pastinha com folhas plásticas (estilo álbum de figurinhas). A criança escolhe folheando a pastinha e bipando o cartão escolhido!

---

## ⚙️ 7. Painel de Configurações (Admin)

Na rota `/admin` você pode ajustar em tempo real:
- **Limite de sessões:** Quantas estrelas a criança acumula antes de entrar na pausa (padrão: 3).
- **Duração da pausa:** Tempo de exibição da tela "Hora de colorir!" com cronômetro visual (padrão: 18 minutos).
- **Modo de contagem:** Contar por *leituras*, *desenhos diferentes* ou *por tempo assistido* (inicia a pausa após X minutos acumulados).
- **Comportamento de bipe durante vídeo:** `Interromper e trocar imediatamente` ou `Ignorar até o vídeo terminar`.
- **Liberação da pausa:** Automática ao fim do cronômetro, apenas por código dos pais ou ambas.
- **Debounce:** Tempo configurável para ignorar bipes repetidos acidentais (padrão: 3 segundos).
- **Perfil do Leitor (USB, 2.4G ou Bluetooth):** Troca imediata sem reiniciar o servidor.
- **Simular Bipe:** Permite testar a TV remotamente digitando o código ou clicando em "Bipar na TV" em qualquer desenho cadastrado.
- **Estatísticas & Favoritos:** Lista com os desenhos mais vistos e contagem total de visualizações.
- **Backup & Restauração:** Exporta um arquivo `.zip` com banco e mídias, ou restaura backups anteriores com validação e segurança.
- **Troca de Senha:** Altere a sua senha de acesso a qualquer momento com confirmação e hash PBKDF2.

---

## 👨‍👩‍👧 8. Controle dos Pais & Monitoramento em Tempo Real (Etapa 3)

O Bipinho oferece ferramentas completas para os pais gerenciarem e acompanharem o uso da TV:

- **Agenda e Limites de Uso Diário:**
  - **Horário permitido:** Defina a janela de início e término (ex: 07:00 às 21:00).
  - **Dias da semana:** Escolha os dias em que a TV pode ser usada (Seg a Dom).
  - **Máximo de sessões por dia:** Limita quantas sessões completas de desenhos a criança pode assistir no dia.
  - **Tela "O Bipinho está dormindo":** Fora dos horários ou dias permitidos, a TV exibe um mascote sonolento amigável com explicação visual clara.
  - **Chave dos Pais Excepcional:** Bipar o cartão secreto dos pais (`PAIS-LIBERAR-99`) libera a TV excepcionalmente para aquela sessão, acordando o Bipinho mesmo fora do horário.
- **Painel ao Vivo (Responsivo para Celular):**
  - Acompanhe em tempo real na aba **"📺 Painel ao Vivo"** o desenho que está tocando, o progresso das estrelas e o tempo assistido.
  - Botões de controle imediato: **▶️ Encerrar Pausa Agora**, **🔒 Bloquear TV** e **🔓 Liberar TV**.
- **Histórico Semanal com Gráfico SVG:**
  - Visualize o tempo de tela diário e o número de sessões dos últimos 7 dias em um gráfico de barras limpo, feito em SVG puro (sem bibliotecas externas).
  - Tabela com os desenhos mais vistos e tempo total assistido a cada dia.
- **Importação em Lote de Pastas do Servidor (📂):**
  - Informe o caminho de uma pasta do PC com vários vídeos/imagens. O sistema cadastra todos automaticamente, gera miniaturas, atribui códigos Code128 e avisa sobre vídeos muito longos ou em resolução muito alta (> 1080p).
- **Cartões de Impressão Separados:**
  - A folha A4 separa a **Chave dos Pais** em uma página própria com aviso em destaque: *"⚠️ NÃO COLOCAR NA PASTINHA DA CRIANÇA"*. O cartão Surpresa permanece junto aos cartões normais.
- **Desafios de Movimento na Pausa:**
  - 15 sugestões pré-cadastradas (ex: "Dê 10 pulinhos!", "Gire como um bailarino!") sorteadas durante a pausa "Hora de colorir!" para incentivar atividade física.

---

## 🎨 9. Experiência da Criança & Atividades Lúdicas (Etapa 4)

O Bipinho foi desenhado com foco no encantamento e na saúde visual da criança:

- **Mascote Animado Bipinho (SVG Puro):**
  - Um leitorzinho simpático com olhinhos que piscam a cada 4 segundos e bracinho que acena suavemente na tela de espera.
  - Ao receber um bipe válido, o mascote pula de alegria, comemora com acenos rápidos e toca um efeito sonoro alegre.
  - Totalmente em código vetorial SVG e CSS puro (leve, sem imagens pesadas e sem bibliotecas externas).
  - Pode ser desativado nas configurações caso os pais prefiram uma tela minimalista.
- **Categorias com Cores Próprias:**
  - Cada desenho é organizado em categorias (Animais, Músicas, Histórias, Educativos ou Geral) com cores vibrantes específicas.
  - Na administração, cada cartão exibe sua etiqueta colorida; nos cartões impressos, uma faixa colorida destaca o tema.
- **Cartão de Contorno para Colorir (Linhas P&B):**
  - Qualquer desenho cadastrado pode ser convertido em uma folha de colorir com um clique no botão **"🖍️ Colorir"** na administração (`/admin/colorir/{id}`).
  - O sistema usa processamento de imagem com detecção de bordas via Pillow para extrair linhas nítidas em preto e branco sobre fundo branco puro, prontas para lápis de cor ou giz de cera.
  - A folha A4 inclui o código de barras para a criança bipar na TV logo após terminar a pintura!
- **Modos de Impressão Flexíveis e Caça ao Tesouro:**
  - **Padrão (6 por folha):** Formato clássico para recortar e colar na pastinha de plástico.
  - **Grandes (2 por folha):** Cartões médios com imagens maiores.
  - **Caça ao Tesouro (1 por folha):** Cartão gigante com borda especial para os pais espalharem pela casa e a criança procurar com o leitor óptico.
  - **Opção de Agrupar por Categoria:** Ordena e organiza os cartões automaticamente antes da impressão.
- **Interface 10-foot UI pura:**
  - Fontes grandes e legíveis a 3 metros de distância do sofá, cores de alto contraste e **nenhum botão ou elemento clicável** na tela da criança.

---

## 🛡️ 10. Segurança & Confiabilidade na TV

- **Screen Wake Lock & Fallback:** Impede a TV de apagar a tela durante o uso com fallback de vídeo mudo para Android TVs antigas.
- **Reconexão Automática com Overlay Amigável:** Quando a conexão SSE cai ou o servidor reinicia, a TV exibe *"Bipinho já volta!"* e reconecta sozinha mantendo as estrelas.
- **Troca Obrigatória de Senha no 1º Acesso:** PBKDF2-HMAC-SHA256 com 100.000 iterações e salt de 16 bytes.
- **Proteção contra Força Bruta (Rate Limiting por IP):** Bloqueio temporário após 5 tentativas incorretas.
- **Restrição de IP:** Opção de permitir acesso à administração exclusivamente pelo PC local (`localhost_only`).
- **Diagnóstico do Sistema:** Monitoramento de FFmpeg, disco, integridade do banco e suspensão de energia do Windows.

---

## 🧪 11. Testes Automatizados

Execute os testes no terminal dentro da pasta do projeto:

```bash
# Testes de Segurança & Diagnóstico (Etapa 1 - 6 testes)
python -m tests.test_etapa1

# Testes de Confiabilidade na TV & Backup (Etapa 2 - 9 testes)
python -m tests.test_etapa2

# Testes de Controle dos Pais, Agenda e Histórico (Etapa 3 - 10 testes)
python -m tests.test_etapa3

# Testes de Experiência da Criança, Categorias e Colorir (Etapa 4 - 7 testes)
python -m tests.test_etapa4

# Teste de Fluxo Completo Original (15 testes)
python -m tests.test_bipinho
```

Todas as 5 suítes (totalizando **47 testes**) passam com 100% de sucesso!
