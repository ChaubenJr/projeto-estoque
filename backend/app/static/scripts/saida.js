$(document).ready(function() {

    // --- Seleção do Elemento ---
    const selectProduto = $('#cod_produto_embalagem');

    // --- PREPARAÇÃO DOS DADOS ---
    // A variável 'produtosData' vem do seu template HTML.
    let produtosParaSelect = produtosData.map(produto => {
        return {
            id: produto.cod_produto_embalagem,
            text: produto.cod_produto_embalagem,
            // Guardamos apenas o 'nome' pois é o único campo a preencher
            nome: produto.nome_produto
        };
    });

    // Adiciona um objeto vazio no início do array para o placeholder.
    produtosParaSelect.unshift({ id: '', text: '' });


    // --- INICIALIZAÇÃO COMPLETA DO SELECT2 (com todo o nosso estilo) ---
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
        }
    });

    // Limpa o campo de descrição quando o usuário clica no "x".
    selectProduto.on('select2:clear', function (e) {
        $(this).val(null).trigger('change');
        $('#nomeProduto').val('');
    });

    // Força o placeholder a ser selecionado no carregamento inicial.
    selectProduto.val(null).trigger('change');

});