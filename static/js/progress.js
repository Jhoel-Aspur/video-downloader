document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('downloadForm');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const message = document.getElementById('message');
    const formatSelect = document.querySelector('select[name="format"]');
    const qualitySelect = document.getElementById('qualitySelect');
    const capybaraLoader = document.getElementById('capybaraLoader');
    const button = form.querySelector('button');

    // Show/hide quality select based on format (not applicable for TikTok)
    if (formatSelect) {
        formatSelect.addEventListener('change', () => {
            qualitySelect.style.display = formatSelect.value === 'mp4' ? 'block' : 'none';
        });
        qualitySelect.style.display = formatSelect.value === 'mp4' ? 'block' : 'none';
    } else {
        qualitySelect.style.display = 'block';
    }

    let pollingInterval = null;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const url = form.querySelector('input[name="url"]').value;
        if (!url.match(/^https?:\/\/(www\.)?(youtube\.com|youtu\.be|facebook\.com|tiktok\.com)/)) {
            message.innerText = '❌ Por favor, ingresa un enlace válido.';
            message.classList.add('error', 'show');
            return;
        }

        progressBar.style.width = '0%';
        progressText.innerText = '0%';
        message.innerText = '';
        message.classList.remove('error', 'show', 'completed');
        progressBar.classList.remove('active', 'completed');
        capybaraLoader.classList.add('visible');
        capybaraLoader.style.display = 'block';
        button.classList.add('loading');
        button.disabled = true;

        const formData = new FormData(form);
        formData.append('platform', form.dataset.platform);

        try {
            const res = await fetch('/download', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();

            if (data.success) {
                pollingInterval = setInterval(async () => {
                    const progressRes = await fetch('/progress');
                    const progressData = await progressRes.json();

                    const loaderLine = capybaraLoader.querySelector('.loaderline');
                    loaderLine.style.width = `${progressData.percent}%`;

                    progressBar.style.width = `${progressData.percent}%`;
                    progressText.innerText = `${progressData.percent.toFixed(1)}%`;
                    message.innerText = progressData.message;
                    message.classList.add('show');
                    progressBar.classList.add('active');

                    if (progressData.status === 'completed') {
                        clearInterval(pollingInterval);
                        button.classList.remove('loading');
                        button.disabled = false;
                        capybaraLoader.classList.remove('visible');
                        capybaraLoader.style.display = 'none';
                        form.reset();
                        if (formatSelect) {
                            qualitySelect.style.display = formatSelect.value === 'mp4' ? 'block' : 'none';
                        }
                        Toastify({
                            text: `✅ Descargado: ${progressData.filename}`,
                            duration: 5000,
                            destination: `/download_file/${encodeURIComponent(progressData.filename)}`,
                            newWindow: false,
                            close: true,
                            gravity: "top",
                            position: "right",
                            backgroundColor: "rgb(204, 125, 45)",
                        }).showToast();
                        message.innerHTML = `
                            <span class="success-check animate-check">✅</span>
                            <span class="success-text">Descarga completada</span>
                            <a href="/download_file/${encodeURIComponent(progressData.filename)}" download class="download-link">${progressData.filename}</a>
                        `;
                        message.classList.add('show', 'completed');
                        progressBar.classList.add('completed');
                        progressBar.style.width = '100%';
                        progressText.innerText = '100%';
                        const downloadLink = message.querySelector('.download-link');
                        if (downloadLink) {
                            downloadLink.click();
                        }
                    } else if (progressData.status === 'error') {
                        clearInterval(pollingInterval);
                        button.classList.remove('loading');
                        button.disabled = false;
                        capybaraLoader.classList.remove('visible');
                        capybaraLoader.style.display = 'none';
                        form.reset();
                        if (formatSelect) {
                            qualitySelect.style.display = formatSelect.value === 'mp4' ? 'block' : 'none';
                        }
                        Toastify({
                            text: `❌ ${progressData.message}`,
                            duration: 5000,
                            close: true,
                            gravity: "top",
                            position: "right",
                            backgroundColor: "#e57373",
                        }).showToast();
                        message.innerText = `❌ ${progressData.message}`;
                        message.classList.add('error', 'show');
                        progressBar.style.width = '0%';
                        progressText.innerText = '0%';
                    }
                }, 1000);
            } else {
                capybaraLoader.classList.remove('visible');
                capybaraLoader.style.display = 'none';
                button.classList.remove('loading');
                button.disabled = false;
                Toastify({
                    text: `❌ Error: ${data.error}`,
                    duration: 5000,
                    close: true,
                    gravity: "top",
                    position: "right",
                    backgroundColor: "#e57373",
                }).showToast();
                message.innerText = `❌ Error: ${data.error}`;
                message.classList.add('error', 'show');
                progressBar.style.width = '0%';
                progressText.innerText = '0%';
            }
        } catch (err) {
            capybaraLoader.classList.remove('visible');
            capybaraLoader.style.display = 'none';
            button.classList.remove('loading');
            button.disabled = false;
            Toastify({
                text: `❌ Error de red: Intenta de nuevo o verifica tu conexión.`,
                duration: 5000,
                close: true,
                gravity: "top",
                position: "right",
                backgroundColor: "#e57373",
            }).showToast();
            message.innerText = `❌ Error de red: Intenta de nuevo o verifica tu conexión.`;
            message.classList.add('error', 'show');
            progressBar.style.width = '0%';
            progressText.innerText = '0%';
        }
    });

    window.addEventListener('beforeunload', () => {
        if (pollingInterval) {
            clearInterval(pollingInterval);
        }
    });
});