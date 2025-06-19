# Validador de Assinaturas Digitais em Massa

Uma aplicação web para validar múltiplas assinaturas digitais em lote e gerar relatórios detalhados com validação criptográfica real.

## Descrição

Este projeto oferece uma forma simples e eficiente de validar assinaturas digitais de múltiplos documentos PDF de uma só vez, similar ao serviço do ITI (https://validar.iti.gov.br/), porém com a capacidade de processar lotes de documentos simultaneamente e gerar relatórios consolidados. Agora com validação criptográfica real e recursos avançados de segurança.

## Funcionalidades

### Validação de Assinaturas
- **Validação criptográfica real** usando a biblioteca `cryptography`
- Upload de múltiplos documentos PDF com assinaturas digitais
- Validação em lote de assinaturas digitais com verificação PAdES
- **Verificação da cadeia de certificados** com validação X.509
- **Extração e análise de certificados** embarcados nas assinaturas
- Verificação de validade temporal dos certificados
- Suporte para diferentes tipos de assinatura digital

### Segurança e Validação de Arquivos
- **Validação rigorosa de arquivos PDF** antes do processamento
- **Detecção de conteúdo malicioso** em PDFs (JavaScript, ações automáticas, etc.)
- Verificação de integridade e estrutura dos arquivos
- Análise de metadata suspeita
- Controle de tamanho máximo de arquivos
- Verificação de cabeçalhos e estruturas PDF

### Gestão de Armazenamento
- **Limpeza automática de arquivos temporários**
- **Sistema de limpeza periódica** para arquivos antigos
- Limpeza automática após processamento dos jobs
- Monitoramento de uso de armazenamento
- Endpoints de administração para gestão manual

### Interface e Relatórios
- Geração de relatório PDF com resultados detalhados
- Interface web simples e intuitiva
- Monitoramento de progresso em tempo real
- Estatísticas detalhadas de validação

## Melhorias de Segurança Implementadas

### 1. Validação Criptográfica Real
- Uso da biblioteca `cryptography` para verificação real de assinaturas
- Parsing e validação de estruturas PKCS#7/CMS
- Extração de certificados X.509 das assinaturas
- Verificação de cadeias de certificados
- Suporte para assinaturas PAdES

### 2. Segurança de Arquivos
- Validação de cabeçalhos PDF
- Detecção de padrões suspeitos (JavaScript, ações automáticas)
- Verificação de integridade estrutural
- Controle de tamanho e número de páginas
- Análise de metadata

### 3. Gestão de Recursos
- Limpeza automática de arquivos temporários
- Sistema de limpeza periódica configurável
- Monitoramento de uso de armazenamento
- Limpeza automática de jobs antigos

## Requisitos

- Python 3.8+
- Bibliotecas Python listadas em `requirements.txt`

## Instalação

1. Clone este repositório:
```bash
git clone https://github.com/Frraz/validador-assinaturas-digitais.git
cd validador-assinaturas-digitais
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Execute a aplicação:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

4. Acesse a aplicação em seu navegador:
```
http://localhost:8000
```

## API Endpoints

### Endpoints Principais
- `POST /upload/` - Upload e validação de arquivos PDF
- `GET /status/{job_id}` - Consultar status de um job de validação
- `GET /report/{job_id}` - Download do relatório PDF

### Endpoints de Administração
- `GET /admin/cleanup` - Executar limpeza manual de arquivos
- `GET /admin/storage-stats` - Obter estatísticas de armazenamento
- `DELETE /admin/job/{job_id}` - Limpar arquivos de um job específico

## Configurações

### Variáveis de Ambiente (Opcionais)
- `MAX_FILE_SIZE` - Tamanho máximo de arquivo (padrão: 100MB)
- `MAX_PAGES` - Número máximo de páginas por PDF (padrão: 1000)
- `CLEANUP_INTERVAL_HOURS` - Intervalo de limpeza automática (padrão: 2 horas)
- `MAX_FILE_AGE_HOURS` - Idade máxima dos arquivos antes da limpeza (padrão: 24 horas)

## Arquitetura do Sistema

### Módulos Principais
- `app/main.py` - Aplicação FastAPI principal com endpoints
- `app/validation/signature_validator.py` - Validação criptográfica de assinaturas
- `app/validation/validation_utils.py` - Utilitários para validação de certificados
- `app/utils/cleanup.py` - Sistema de limpeza automática
- `app/utils/pdf_security.py` - Validação de segurança de PDFs
- `app/report/pdf_generator.py` - Geração de relatórios

### Fluxo de Validação
1. **Upload** - Arquivos são enviados e validados quanto à segurança
2. **Processamento** - Cada PDF é analisado para extrair assinaturas
3. **Validação Criptográfica** - Verificação real das assinaturas e certificados
4. **Geração de Relatório** - Criação de relatório detalhado em PDF
5. **Limpeza Automática** - Remoção automática de arquivos temporários

## Recursos de Segurança

### Validação de Arquivos
- Verificação de cabeçalhos PDF válidos
- Detecção de JavaScript e código malicioso
- Análise de ações automáticas suspeitas
- Verificação de tamanho e estrutura
- Análise de metadados

### Validação de Assinaturas
- Parsing de estruturas PKCS#7/CMS
- Extração de certificados X.509
- Verificação de cadeia de certificados
- Validação temporal de certificados
- Suporte para padrões PAdES

### Gestão de Recursos
- Limpeza automática configurável
- Monitoramento de uso de disco
- Controle de idade de arquivos
- Remoção segura de dados temporários

## Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo LICENSE para detalhes.

## Contribuição

Contribuições são bem-vindas! Por favor, abra uma issue ou envie um pull request.

## Suporte

Para suporte ou dúvidas, abra uma issue no repositório GitHub.