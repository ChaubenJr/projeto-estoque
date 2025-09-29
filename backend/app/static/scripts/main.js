// Em app/static/scripts/main.js

// Garante que todo o código só rode depois que a página estiver totalmente carregada
$(document).ready(function() {

    // --- Seleção dos Elementos ---
    const selectProduto = $('#cod_produto_embalagem');
    const nomeProduto   = $('#nomeProduto');
    const padraoProduto = $('#padraoProduto');
    const undProduto    = $('#und');

    // --- Preparação dos Dados ---
    // Transforma a lista de produtos vinda do Flask em um objeto mais fácil de usar
    const produtos = produtosData.reduce((acc, produto) => {
        acc[produto.cod_produto_embalagem] = {
            nome: produto.nome_produto,
            padrao: produto.padrao_embalagem,
            unidade: produto.unidade_medida
        };
        return acc;
    }, {});

    // --- Populando o Select com os Produtos ---
    // Limpa quaisquer opções antigas antes de adicionar novas
    selectProduto.empty().append(new Option('Selecione...', ''));
    for (let codigo in produtos) {
        selectProduto.append(new Option(codigo, codigo));
    }

    // --- INICIALIZAÇÃO ÚNICA E CORRETA DO SELECT2 ---
    selectProduto.select2({
    width: '100%',                      // Mantém o dropdown com a largura total
    minimumResultsForSearch: Infinity   // Mantém a remoção da busca
    });

    // Adiciona uma classe do Bootstrap para consistência visual (opcional, mas bom)
    selectProduto.next('.select2-container').find('.select2-selection').addClass('form-select');

    // --- Evento de Mudança (quando um produto é selecionado) ---
    selectProduto.on('change', function() {
        const codigo = $(this).val();
        if (codigo && produtos[codigo]) {
            nomeProduto.val(produtos[codigo].nome);
            padraoProduto.val(produtos[codigo].padrao);
            undProduto.val(produtos[codigo].unidade);
        } else {
            // Limpa os campos se "Selecione..." for escolhido
            nomeProduto.val('');
            padraoProduto.val('');
            undProduto.val('');
        }
    });

});

document.querySelectorAll('.number-input-wrapper').forEach(wrapper => {
    const input = wrapper.querySelector('input[type="number"]');
    const arrowUp = wrapper.querySelector('.arrow-up');
    const arrowDown = wrapper.querySelector('.arrow-down');

    arrowUp.addEventListener('click', () => {
        input.stepUp();
    });

    arrowDown.addEventListener('click', () => {
        input.stepDown();
    });
});