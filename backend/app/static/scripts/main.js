// Quando a página carrega, adiciona os listeners aos botões
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('btnRegistro')
    .addEventListener('click', () => {
        window.location.href = 'registro-diario.html';
    });

    document.getElementById('btnSaida')
    .addEventListener('click', () => {
        window.location.href = 'saida.html';
    });
});