# 📋 Checklist de Verificação Manual na TV Real (Bipinho)

Este documento contém o roteiro de testes e validação manual para ser executado no ambiente real de funcionamento do **Bipinho**:
- **Servidor:** PC Windows na rede local rodando o Bipinho (`python run.py` ou `bipinho.exe`).
- **Cliente:** Android TV ou Smart TV conectada via Wi-Fi/Cabo à mesma rede local, abrindo o navegador (Chrome, TV Bro, Puffin ou Silk Browser) em `http://<IP_DO_PC>:8000/tv`.
- **Dispositivo de Entrada:** Leitor de código de barras USB/2.4G/Bluetooth emparelhado com a TV (atuando como teclado).

---

## 🗂️ Índice dos Testes

1. [Teste 1: Acesso Inicial e Carregamento da TV](#teste-1-acesso-inicial-e-carregamento-da-tv)
2. [Teste 2: Impedimento de Apagamento de Tela (Screen Wake Lock)](#teste-2-impedimento-de-apagamento-de-tela-screen-wake-lock)
3. [Teste 3: Reconexão Automática do SSE ("Bipinho já volta!")](#teste-3-reconexão-automática-do-sse-bipinho-já-volta)
4. [Teste 4: Comportamento de Bipe Durante Reprodução de Vídeo](#teste-4-comportamento-de-bipe-durante-reprodução-de-vídeo)
5. [Teste 5: Modo de Contagem por Tempo Assistido](#teste-5-modo-de-contagem-por-tempo-assistido)
6. [Teste 6: Limite Diário e Horário de Dormir ("O Bipinho está dormindo")](#teste-6-limite-diário-e-horário-de-dormir-o-bipinho-está-dormindo)
7. [Teste 7: Liberação Excepcional via Chave dos Pais](#teste-7-liberação-excepcional-via-chave-dos-pais)
8. [Teste 8: Impressão e Leitura dos Cartões de Código de Barras](#teste-8-impressão-e-leitura-dos-cartões-de-código-de-barras)
9. [Teste 9: Cartão de Contorno para Colorir (P&B)](#teste-9-cartão-de-contorno-para-colorir-pb)
10. [Teste 10: Mascote Animado e Interface 10-foot UI](#teste-10-mascote-animado-e-interface-10-foot-ui)
11. [Teste 11: Exportação e Restauração de Backup](#teste-11-exportação-e-restauração-de-backup)

---

## Teste 1: Acesso Inicial e Carregamento da TV

- [ ] **1.1 Identificar IP do PC:** No PC, execute `ipconfig` ou veja na página `/admin` o IP sugerido (ex: `192.168.1.100:8000`).
- [ ] **1.2 Acessar pela TV:** No navegador da TV, acesse `http://192.168.1.100:8000/tv`.
- [ ] **1.3 Tela de Espera:** A tela abre em modo de espera exibindo o título, o mascote animado e a mensagem *"Aponte o leitor para o cartão do seu desenho favorito!"*.
- [ ] **1.4 Sem Elementos Clicáveis:** Confirme que não há botões, links ou cursores visíveis (10-foot UI pura).
- [ ] **1.5 Tela Cheia:** Ative o modo tela cheia no navegador da TV (F11 ou opção do navegador) se necessário.

---

## Teste 2: Impedimento de Apagamento de Tela (Screen Wake Lock)

- [ ] **2.1 Modo Wake Lock Ativo:** Abra o Console da TV (se disponível) ou observe se a TV não escurece a tela após o tempo padrão de inatividade (ex: 5 ou 10 minutos).
- [ ] **2.2 Fallback de Vídeo Invisível:** Caso o navegador da TV não suporte a `Screen Wake Lock API`, o Bipinho ativa automaticamente um vídeo de 1x1 pixel em loop mudo para manter o display ativo.
- [ ] **2.3 Diagnóstico no PC:** No PC, acesse `/admin` > aba **Diagnóstico** e verifique se o aviso de energia do Windows indica se a suspensão está habilitada no PC servidor.

---

## Teste 3: Reconexão Automática do SSE ("Bipinho já volta!")

- [ ] **3.1 Simular Perda de Conexão:** No PC, encerre temporariamente o servidor (`Ctrl + C` no terminal) ou desconecte o cabo de rede/Wi-Fi do PC por 10 segundos.
- [ ] **3.2 Mensagem Amigável:** Na TV, observe que surge um aviso flutuante elegante e amigável:
  > *"📡 Bipinho já volta! Reconectando..."*
- [ ] **3.3 Reconexão Transparente:** Reinicie o servidor no PC (`python run.py`).
- [ ] **3.4 Retorno Automático:** Dentro de 2 a 5 segundos, a TV detecta o servidor de volta, o aviso desaparece e a sessão é restabelecida sem recarregar a página e sem perder as estrelas acumuladas.

---

## Teste 4: Comportamento de Bipe Durante Reprodução de Vídeo

### Cenário A: Modo "Interromper e trocar imediatamente" (Padrão)
- [ ] **4.1 Configuração:** No PC em `/admin` > **Configurações da Sessão**, selecione `Interromper e trocar imediatamente` e salve.
- [ ] **4.2 Bipe Inicial:** Bipe um cartão de vídeo longo (ex: 5 minutos). O vídeo inicia imediatamente.
- [ ] **4.3 Bipe Durante o Vídeo:** Após 10 segundos, bipe um cartão diferente.
- [ ] **4.4 Resultado Esperado:** O vídeo em reprodução é interrompido imediatamente e o novo desenho começa a tocar. A estrela correspondente é contabilizada conforme as regras.

### Cenário B: Modo "Ignorar até o vídeo terminar"
- [ ] **4.5 Configuração:** No PC em `/admin`, altere para `Ignorar até o vídeo terminar` e salve.
- [ ] **4.6 Bipe Durante o Vídeo:** Enquanto o vídeo estiver tocando, bipe outro cartão.
- [ ] **4.7 Resultado Esperado:** A TV ignora o novo bipe, não troca de vídeo e continua reproduzindo o atual até o fim.
- [ ] **4.8 Bipe Após Término:** Ao terminar o vídeo, a TV volta para a tela de espera. Bipar o cartão agora inicia normalmente.

---

## Teste 5: Modo de Contagem por Tempo Assistido

- [ ] **5.1 Configuração:** No PC em `/admin`, configure:
  - **Modo de Contagem:** `Tempo assistido de tela (minutos)`
  - **Minutos para iniciar a pausa:** `1` (para teste rápido).
- [ ] **5.2 Início da Sessão:** Na TV, bipe um desenho e deixe rodar por 60 segundos.
- [ ] **5.3 Ativação da Pausa:** Imediatamente após completar 1 minuto acumulado de vídeo assistido, a tela comuta automaticamente para a pausa:
  > *"⏰ Hora de colorir!"* com cronômetro regressivo e o desafio de movimento sorteado.
- [ ] **5.4 Bloqueio de Bipes Normais na Pausa:** Bipar cartões de desenhos normais emite som de aviso ou ignora, mantendo a pausa até o tempo acabar.

---

## Teste 6: Limite Diário e Horário de Dormir ("O Bipinho está dormindo")

- [ ] **6.1 Configurar Horário de Bloqueio:** No PC em `/admin` > **Controle dos Pais**:
  - Altere o **Horário Permitido** para uma faixa fora do horário atual (ex: se são 15:00, configure das 18:00 às 20:00).
- [ ] **6.2 Tela de Dormir na TV:** Na TV, a tela deve exibir imediatamente:
  > *"🌙 O Bipinho está dormindo! Volte amanhã ou no horário combinado."* com o mascote de olhinhos fechados.
- [ ] **6.3 Tentativa de Leitura:** Bipar um cartão de desenho qualquer enquanto dorme não toca o desenho e mantém a tela de descanso.

---

## Teste 7: Liberação Excepcional via Chave dos Pais

- [ ] **7.1 Cartão Secreto dos Pais:** Tenha em mãos o cartão impresso da **Chave dos Pais** (`PAIS-LIBERAR-99`).
- [ ] **7.2 Bipar na Tela de Dormir:** Com a TV na tela *"O Bipinho está dormindo"*, aponte o leitor para o código da Chave dos Pais.
- [ ] **7.3 Resultado Esperado:** O Bipinho "acorda" imediatamente, toca o som alegre de liberação, a TV volta à tela de espera e permite assistir a uma sessão normalmente.
- [ ] **7.4 Liberação de Pausa:** Durante a pausa *"Hora de colorir!"*, bipar a Chave dos Pais encerra a pausa imediatamente e libera a TV para novo desenho.

---

## Teste 8: Impressão e Leitura dos Cartões de Código de Barras

- [ ] **8.1 Visualização de Impressão:** Acesse `/admin/imprimir-cartoes`.
- [ ] **8.2 Separação da Chave dos Pais:** Verifique que a primeira página contém os cartões normais e a Chave dos Pais está em página destacada com o aviso:
  > *"⚠️ NÃO COLOCAR NA PASTINHA DA CRIANÇA - Guarde com você para liberar a TV quando necessário."*
- [ ] **8.3 Modos de Layout:**
  - Teste alternar entre **Padrão (6 por folha)**, **Grandes (2 por folha)** e **Caça ao Tesouro (1 por folha)**.
  - Teste a opção **Agrupar por categoria** e confirme as faixas coloridas (ex: Animais em verde, Músicas em amarelo).
- [ ] **8.4 Leitura Física:** Imprima uma página de teste em folha A4 comum. Aponte o leitor de código de barras a uma distância de 10 a 20 cm do papel e certifique-se de que a leitura na TV é rápida e precisa (< 300ms).

---

## Teste 9: Cartão de Contorno para Colorir (P&B)

- [ ] **9.1 Acessar Desenho:** No PC em `/admin`, localize qualquer desenho na lista e clique no botão **"🖍️ Colorir"**.
- [ ] **9.2 Renderização da Página:** A rota `/admin/colorir/{id}` deve abrir uma página otimizada para A4 contendo:
  - Título do desenho em destaque.
  - Imagem do desenho convertida em contornos pretos sobre fundo branco puro (ideal para economia de tinta e fácil de pintar).
  - Código de barras na parte inferior para a criança bipar na TV após colorir.
- [ ] **9.3 Impressão P&B:** Clique em Imprimir e verifique se a folha sai limpa, com linhas nítidas sem tons escuros borrados.

---

## Teste 10: Mascote Animado e Interface 10-foot UI

- [ ] **10.1 Piscar de Olhos:** Na tela de espera da TV, observe o mascote SVG Bipinho piscar suavemente a cada 4 segundos.
- [ ] **10.2 Aceno de Braço:** Observe o bracinho do leitorzinho acenar periodicamente.
- [ ] **10.3 Reação ao Bipe:** Ao bipar um cartão válido, o mascote salta de alegria na tela antes de abrir o vídeo.
- [ ] **10.4 Desativação (Opcional):** Em `/admin` > **Aparência e Mascote**, desmarque "Exibir Mascote Animado" e salve. Na TV, o mascote deve sumir dando lugar a um ícone estático simplificado.

---

## Teste 11: Exportação e Restauração de Backup

- [ ] **11.1 Exportar Backup:** Em `/admin` > aba **Backup & Restauração**, clique em **"📥 Baixar Backup Completo (.zip)"**.
- [ ] **11.2 Verificação do Arquivo:** O download do arquivo `bipinho_backup_YYYYMMDD_HHMMSS.zip` deve ser concluído. Abra o `.zip` e confirme que ele contém:
  - `data/bipinho.db`
  - `media/uploads/`
  - `media/thumbs/`
- [ ] **11.3 Restauração de Teste:** Faça o upload do arquivo gerado no campo de restauração e clique em **"Restaurar Backup"**.
- [ ] **11.4 Integridade dos Dados:** O sistema deve validar o ZIP, restaurar o banco e as mídias, e reiniciar sem perda de dados.

---

## 🏁 Conclusão da Homologação

| Item | Status | Observações |
|---|:---:|---|
| Conexão e Navegador TV | [ ] APROVADO | |
| Screen Wake Lock | [ ] APROVADO | |
| Reconexão Automática | [ ] APROVADO | |
| Comportamento de Bipe | [ ] APROVADO | |
| Tempo Assistido | [ ] APROVADO | |
| Horário e Dormir | [ ] APROVADO | |
| Chave dos Pais | [ ] APROVADO | |
| Leitor de Barras | [ ] APROVADO | |
| Páginas de Colorir | [ ] APROVADO | |
| Mascote SVG | [ ] APROVADO | |
| Backup e Restauração | [ ] APROVADO | |

**Responsável pelos Testes:** ___________________________  
**Data da Validação:** _____ / _____ / 2026
