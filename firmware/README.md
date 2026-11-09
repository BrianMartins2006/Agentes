# ESP32 com troca de rede pelo celular

Firmware preparado após autorização do usuário. Mantém DHT11 GPIO4, solo GPIO34,
calibração 4095/2901 e o formato HTML consumido pelo coletor. Não inclui as
credenciais Wi-Fi compartilhadas anteriormente. Este sketch ainda não foi compilado
ou gravado em hardware nesta sessão.

## Preparar no Arduino IDE

1. Instale o suporte de placas ESP32 e selecione o modelo real da sua placa/porta.
2. Instale pelo Gerenciador de Bibliotecas **WiFiManager**, autor **tzapu**,
   **DHT sensor library**, da Adafruit, e sua dependência **Adafruit Unified Sensor**.
3. Abra `monitoramento_ambiental/monitoramento_ambiental.ino`.
4. Personalize `portalPassword` (mínimo 8 caracteres). Essa senha protege a rede de
   configuração; não é a senha do roteador.
5. Compile e grave por USB. Abra o Monitor Serial em 115200 baud.

## Usar em outra rede

1. Ligue a placa no novo local. Ela tenta a última rede salva por até 20 segundos.
2. Se não conectar, cria a rede `Ambiente-ESP32-XXXXXX`, identificada também no Serial.
3. No celular, conecte nessa rede usando a senha `portalPassword` do sketch.
   Aceite permanecer conectado mesmo sem acesso à internet.
4. Abra `http://192.168.4.1` se a página de configuração não abrir automaticamente.
5. Escolha **Configure WiFi**, selecione a rede do local, informe a senha e salve.
6. A placa tenta conectar; após sucesso, o painel passa a usar o IP atribuído pelo
   roteador, mostrado no Monitor Serial. O celular deve voltar à rede do local
   para acessar esse painel. `192.168.4.1` é o portal de configuração, não um IP
   permanente de monitoramento.

O portal fica disponível por cinco minutos; se não concluir, a placa reinicia e
repete a tentativa. As credenciais válidas ficam salvas para os próximos boots.
Se cair o Wi-Fi durante o funcionamento, a placa tenta reconectar; após 60 segundos
sem conexão, reinicia e repete a rotina de conexão/portal.

Se quiser trocar de rede enquanto a antiga ainda funciona, digite `w` no Monitor
Serial: isso apaga as credenciais Wi-Fi e reinicia em configuração. Não há comando
remoto aberto para apagar a rede. Não foi adicionado botão ou alterada a fiação.

## O que acontece com o backend

Nesta versão, a coleta ainda passa pelo computador/Raspberry Pi na mesma rede da
ESP32. Atualize `ESP32_URL` no `.env` para o novo IP e reinicie o coletor. Se o IP
mudar novamente pelo DHCP, essa configuração precisa ser atualizada novamente.
O portal resolve a troca das credenciais Wi-Fi, não a descoberta automática do IP.
Redes com isolamento entre dispositivos podem impedir a coleta local.

A evolução para eliminar essa configuração de IP é a ESP32 enviar medições por
HTTPS ao endereço fixo da API na Render. Esse envio direto ainda não foi
implementado neste sketch. Exigirá configuração de URL/chave do dispositivo,
validação do certificado TLS, sincronização do relógio e tratamento de falhas.
O Supabase permanecerá acessível somente pelo backend, sem senha do banco na placa.

## Validação na placa

- Primeira configuração pelo celular e acesso ao painel na rede escolhida.
- Reinício com reconexão automática e manutenção das credenciais.
- Troca para uma segunda rede e atualização do coletor para o novo IP.
- Queda temporária da rede, recuperação e ausência prolongada abrindo o portal.
- Comando `w`, senha incorreta e expiração do portal sem configuração.
- Leituras reais do DHT11/solo e compatibilidade com o coletor existente.

Referência: [WiFiManager oficial](https://github.com/tzapu/WiFiManager).
