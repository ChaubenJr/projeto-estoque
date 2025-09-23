// Aguarda o carregamento completo do DOM para garantir que todos os elementos estão disponíveis.
document.addEventListener('DOMContentLoaded', function() {
    // Inicializa o Select2 nos dropdowns com a classe 'form-select'.
    // O Select2 torna o dropdown mais fácil de usar, com funcionalidades de busca.
    const selectElements = document.querySelectorAll('.form-select');
    selectElements.forEach(select => {
        $(select).select2({
            theme: "bootstrap-5",
            width: $(select).data('width') ? $(select).data('width') : $(select).hasClass('w-100') ? '100%' : 'style',
            placeholder: $(select).data('placeholder'),
        });
    });

    // Encontra o elemento de seleção do código do produto pelo ID.
    const codProdutoEmbalagemSelect = document.getElementById('cod_produto_embalagem');
    // Encontra os campos de entrada que serão preenchidos automaticamente.
    const nomeProdutoInput = document.getElementById('nomeProduto');
    const unidadeMedidaInput = document.getElementById('und');
    const padraoEmbalagemInput = document.getElementById('padraoProduto');

    // Verifica se os dados dos produtos foram carregados e se os elementos HTML existem.
    if (typeof produtosData !== 'undefined' && codProdutoEmbalagemSelect && nomeProdutoInput && unidadeMedidaInput && padraoEmbalagemInput) {
        // Itera sobre os dados dos produtos e adiciona uma opção ao dropdown para cada um.
        produtosData.forEach(produto => {
            const option = new Option(produto.cod_produto_embalagem, produto.cod_produto_embalagem);
            // Armazena as descrições completas do produto nos atributos de dados do elemento da opção.
            option.dataset.nomeProduto = produto.nome_produto;
            option.dataset.unidadeMedida = produto.unidade_medida;
            option.dataset.padraoEmbalagem = produto.padrao_embalagem;
            codProdutoEmbalagemSelect.appendChild(option);
        });
        
        // Adiciona um listener de evento para o dropdown do código do produto.
        $(codProdutoEmbalagemSelect).on('change', function() {
            const selectedOption = $(this).find('option:selected');
            const nomeProduto = selectedOption.data('nome-produto');
            const unidadeMedida = selectedOption.data('unidade-medida');
            const padraoEmbalagem = selectedOption.data('padrao-embalagem');

            nomeProdutoInput.value = nomeProduto || '';
            unidadeMedidaInput.value = unidadeMedida || '';
            padraoEmbalagemInput.value = padraoEmbalagem || '';
        }).trigger('change');
    }

    // Função para lidar com o envio do formulário de entrada.
    function handleEntradaSubmit(event) {
        const quantidade = document.getElementById('quantidade_recebida');
        const total = document.getElementById('total');
        if (parseInt(quantidade.value) > parseInt(total.value)) {
            // Impede o envio do formulário se a validação falhar.
            event.preventDefault();
            // Substitui o `alert` por uma mensagem personalizada para evitar bloqueios.
            const feedback = document.createElement('div');
            feedback.className = 'alert alert-danger';
            feedback.textContent = "A quantidade recebida não pode ser maior que o total da nota fiscal.";
            document.querySelector('.card-body').prepend(feedback);
            setTimeout(() => {
                feedback.remove();
            }, 5000);
            return false;
        }
        return true;
    }
    
    // Anexa o manipulador de eventos ao formulário de entrada, se existir.
    const entradaForm = document.querySelector('form[action="{{ url_for('main.entrada_embalagem') }}"]');
    if (entradaForm) {
        entradaForm.addEventListener('submit', handleEntradaSubmit);
    }
});
