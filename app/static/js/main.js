document.addEventListener('DOMContentLoaded', function() {
    // Elementos da interface
    const dropArea = document.getElementById('dropArea');
    const fileInput = document.getElementById('fileInput');
    const selectFilesBtn = document.getElementById('selectFilesBtn');
    const fileList = document.getElementById('fileList');
    const selectedFilesList = document.getElementById('selectedFilesList');
    const uploadBtn = document.getElementById('uploadBtn');
    const clearBtn = document.getElementById('clearBtn');
    const validationStatus = document.getElementById('validationStatus');
    const progressBar = document.getElementById('progressValue');
    const progressText = document.getElementById('progressText');
    const fileStatusList = document.getElementById('fileStatusList');
    const reportActions = document.getElementById('reportActions');
    const downloadReportBtn = document.getElementById('downloadReportBtn');
    const newValidationBtn = document.getElementById('newValidationBtn');
    
    // Armazenamento de arquivos selecionados e informações de trabalho
    let selectedFiles = [];
    let currentJobId = null;
    let statusCheckInterval = null;
    
    // Inicializar event listeners
    initEventListeners();
    
    function initEventListeners() {
        // Evento para seleção de arquivos através do botão
        selectFilesBtn.addEventListener('click', () => {
            fileInput.click();
        });
        
        // Evento para seleção de arquivos via input
        fileInput.addEventListener('change', (e) => {
            handleFilesSelected(e.target.files);
        });
        
        // Eventos para drag and drop
        dropArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropArea.classList.add('active');
        });
        
        dropArea.addEventListener('dragleave', () => {
            dropArea.classList.remove('active');
        });
        
        dropArea.addEventListener('drop', (e) => {
            e.preventDefault();
            dropArea.classList.remove('active');
            handleFilesSelected(e.dataTransfer.files);
        });
        
        // Botão para iniciar upload e validação
        uploadBtn.addEventListener('click', startValidation);
        
        // Botão para limpar seleção
        clearBtn.addEventListener('click', clearSelectedFiles);
        
        // Botão para baixar relatório
        downloadReportBtn.addEventListener('click', downloadReport);
        
        // Botão para nova validação
        newValidationBtn.addEventListener('click', resetApplication);
    }
    
    function handleFilesSelected(files) {
        // Filtrar apenas arquivos PDF
        const pdfFiles = Array.from(files).filter(file => file.type === 'application/pdf');
        
        // Se nenhum arquivo PDF foi selecionado, mostrar alerta
        if (pdfFiles.length === 0) {
            alert('Por favor, selecione apenas arquivos PDF.');
            return;
        }
        
        // Adicionar arquivos à lista de selecionados
        for (const file of pdfFiles) {
            // Verificar se o arquivo já está na lista (usando nome como identificador)
            if (!selectedFiles.some(f => f.name === file.name)) {
                selectedFiles.push(file);
            }
        }
        
        // Atualizar interface
        updateSelectedFilesList();
    }
    
    function updateSelectedFilesList() {
        // Limpar lista atual
        selectedFilesList.innerHTML = '';
        
        // Se houver arquivos, exibir a seção da lista
        if (selectedFiles.length > 0) {
            fileList.style.display = 'block';
            
            // Adicionar cada arquivo à lista de exibição
            selectedFiles.forEach((file, index) => {
                const li = document.createElement('li');
                
                const fileInfo = document.createElement('span');
                fileInfo.textContent = `${file.name} (${formatFileSize(file.size)})`;
                
                const removeBtn = document.createElement('span');
                removeBtn.classList.add('remove');
                removeBtn.textContent = '✕';
                removeBtn.addEventListener('click', () => removeFile(index));
                
                li.appendChild(fileInfo);
                li.appendChild(removeBtn);
                selectedFilesList.appendChild(li);
            });
        } else {
            fileList.style.display = 'none';
        }
    }
    
    function removeFile(index) {
        selectedFiles.splice(index, 1);
        updateSelectedFilesList();
    }
    
    function clearSelectedFiles() {
        selectedFiles = [];
        fileInput.value = '';
        updateSelectedFilesList();
    }
    
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    async function startValidation() {
        if (selectedFiles.length === 0) {
            alert('Por favor, selecione pelo menos um arquivo PDF para validação.');
            return;
        }
        
        try {
            // Preparar formData para upload
            const formData = new FormData();
            selectedFiles.forEach(file => {
                formData.append('files', file);
            });
            
            // Enviar arquivos para o servidor
            const response = await fetch('/upload/', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error('Falha no upload dos arquivos');
            }
            
            const data = await response.json();
            currentJobId = data.job_id;
            
            // Atualizar interface para mostrar progresso
            validationStatus.style.display = 'block';
            fileList.style.display = 'none';
            dropArea.style.display = 'none';
            
            // Iniciar verificação periódica de status
            startStatusCheck();
            
        } catch (error) {
            console.error('Erro ao iniciar validação:', error);
            alert('Ocorreu um erro ao iniciar a validação. Por favor, tente novamente.');
        }
    }
    
    function startStatusCheck() {
        // Verificar status imediatamente
        checkJobStatus();
        
        // Configurar verificações periódicas (a cada 2 segundos)
        statusCheckInterval = setInterval(checkJobStatus, 2000);
    }
    
    async function checkJobStatus() {
        if (!currentJobId) return;
        
        try {
            const response = await fetch(`/status/${currentJobId}`);
            
            if (!response.ok) {
                throw new Error('Falha ao obter status do trabalho');
            }
            
            const jobStatus = await response.json();
            
            // Atualizar interface com o status atual
            updateStatusUI(jobStatus);
            
            // Se o trabalho estiver concluído, parar as verificações
            if (jobStatus.status === 'completo') {
                clearInterval(statusCheckInterval);
                statusCheckInterval = null;
                showCompleteStatus(jobStatus);
            }
            
        } catch (error) {
            console.error('Erro ao verificar status:', error);
            
            // Em caso de erro, parar verificações
            if (statusCheckInterval) {
                clearInterval(statusCheckInterval);
                statusCheckInterval = null;
            }
        }
    }
    
    function updateStatusUI(jobStatus) {
        // Atualizar barra de progresso
        const progress = jobStatus.progress || 0;
        progressBar.style.width = `${progress}%`;
        progressText.textContent = `${progress}%`;
        
        // Atualizar lista de status dos arquivos
        fileStatusList.innerHTML = '';
        
        if (jobStatus.files && jobStatus.files.length > 0) {
            jobStatus.files.forEach(file => {
                const fileItem = document.createElement('div');
                fileItem.classList.add('file-item');
                
                const fileName = document.createElement('div');
                fileName.classList.add('file-name');
                fileName.textContent = file.filename;
                
                const statusBadge = document.createElement('div');
                statusBadge.classList.add('status-badge');
                
                // Definir classe e texto com base no status
                let statusClass = 'status-pending';
                let statusText = 'Pendente';
                
                if (file.status === 'validado') {
                    if (file.is_valid) {
                        statusClass = 'status-valid';
                        statusText = 'Assinatura Válida';
                    } else {
                        statusClass = 'status-invalid';
                        statusText = 'Assinatura Inválida';
                    }
                } else if (file.status === 'erro') {
                    statusClass = 'status-error';
                    statusText = 'Erro';
                } else if (file.status === 'processando') {
                    statusClass = 'status-validating';
                    statusText = 'Validando...';
                }
                
                statusBadge.classList.add(statusClass);
                statusBadge.textContent = statusText;
                
                fileItem.appendChild(fileName);
                fileItem.appendChild(statusBadge);
                fileStatusList.appendChild(fileItem);
            });
        }
    }
    
    function showCompleteStatus(jobStatus) {
        // Mostrar botões de ação final
        reportActions.style.display = 'flex';
        
        // Se houver relatório disponível, configurar botão de download
        if (jobStatus.report_path) {
            downloadReportBtn.disabled = false;
        } else {
            downloadReportBtn.disabled = true;
        }
    }
    
    function downloadReport() {
        if (currentJobId) {
            // Abrir relatório em nova aba
            window.open(`/report/${currentJobId}`, '_blank');
        }
    }
    
    function resetApplication() {
        // Limpar dados
        selectedFiles = [];
        currentJobId = null;
        fileInput.value = '';
        
        // Resetar interface
        dropArea.style.display = 'block';
        fileList.style.display = 'none';
        validationStatus.style.display = 'none';
        reportActions.style.display = 'none';
        
        // Limpar listas
        selectedFilesList.innerHTML = '';
        fileStatusList.innerHTML = '';
        
        // Resetar progresso
        progressBar.style.width = '0%';
        progressText.textContent = '0%';
        
        // Encerrar verificações de status se houver
        if (statusCheckInterval) {
            clearInterval(statusCheckInterval);
            statusCheckInterval = null;
        }
    }
});