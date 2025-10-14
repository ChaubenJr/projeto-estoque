$(document).ready(function() {

    // --- Seleção do Elemento ---
    const selectProduto = $('#cod_produto_embalagem');

    // --- PREPARAÇÃO DOS DADOS ---
    // A variável 'produtosData' vem do seu template HTML.
    let produtosParaSelect = produtosData.map(produto => {
        return {
            id: produto.cod_produto_embalagem,
            text: produto.cod_produto_embalagem,
            nome: produto.nome_produto,
            padrao: produto.padrao_embalagem,
            unidade: produto.unidade_medida
        };
    });

    // ✅ --- A CORREÇÃO ESTÁ AQUI --- ✅
    // Adiciona um objeto vazio no início do array.
    // Este objeto funcionará como o nosso placeholder.
    produtosParaSelect.unshift({ id: '', text: '' });


    // --- INICIALIZAÇÃO CORRETA E COMPLETA DO SELECT2 ---
    selectProduto.select2({
        data: produtosParaSelect,
        placeholder: 'Selecione ou digite um código...',
        allowClear: true,
        width: '100%',
        dropdownParent: $(document.body)
    });


    // --- EVENTO DE MUDANÇA (quando um produto é selecionado) ---
    selectProduto.on('select2:select', function(e) {
        const data = e.params.data;
        
        if (data && data.id) {
            $('#nomeProduto').val(data.nome);
            $('#padraoProduto').val(data.padrao);
            $('#und').val(data.unidade);
        }
    });

    // Limpa os campos quando o usuário clica no "x" do placeholder.
    selectProduto.on('select2:clear', function (e) {
        // Precisamos limpar o valor do select também
        $(this).val(null).trigger('change');

        // E limpar os outros campos
        $('#nomeProduto').val('');
        $('#padraoProduto').val('');
        $('#und').val('');
    });

    // Força o placeholder a ser selecionado no carregamento inicial
    selectProduto.val(null).trigger('change');

    $('#hora_recebimento').on('focus', function() {
            const campoHora = $(this);

            // Apenas preenche se o campo estiver vazio,
            // para não sobrescrever um valor digitado pelo usuário.
            if (campoHora.val() === '') {
                const dataAtual = new Date();

                // Pega a hora e os minutos e formata para ter sempre dois dígitos
                const horas = String(dataAtual.getHours()).padStart(2, '0');
                const minutos = String(dataAtual.getMinutes()).padStart(2, '0');

                // Define o valor do campo com a hora formatada (HH:MM)
                campoHora.val(`${horas}:${minutos}`);
            }
    });
});
