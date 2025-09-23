// Transforma a lista de produtos vinda do Flask em um objeto mais fácil de usar
const produtos = produtosData.reduce((acc, produto) => {
  acc[produto.cod_produto_embalagem] = {
    nome: produto.nome_produto,
    padrao: produto.padrao_embalagem,
    unidade: produto.unidade_medida
  };
  return acc;
}, {});

$(document).ready(function() {
  const selectProduto = $('#cod_produto_embalagem');
  const nomeProduto   = $('#nomeProduto');
  const padraoProduto = $('#padraoProduto');
  const undProduto    = $('#und');

  // popula select
  for (let codigo in produtos) {
    selectProduto.append(new Option(codigo, codigo));
  }
  // Adiciona uma opção para o nome do produto também, se desejar
  // produtosData.forEach(p => selectProduto.append(new Option(`${p.cod_produto_embalagem} - ${p.nome_produto}`, p.cod_produto_embalagem)));

  // agora sim inicializa o select2
  selectProduto.select2({
    dropdownParent: $('.container'),
    dropdownAutoWidth: true,
    width: '100%' 
  });
  $('.select2-selection').addClass('form-select');

  // evento change
  selectProduto.on('change', function() {
    const codigo = $(this).val();
    if (produtos[codigo]) {
      nomeProduto.val(produtos[codigo].nome);
      padraoProduto.val(produtos[codigo].padrao);
      undProduto.val(produtos[codigo].unidade);
    } else {
      nomeProduto.val('');
      padraoProduto.val('');
      undProduto.val('');
    }
  });
});
