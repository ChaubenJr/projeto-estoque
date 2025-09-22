// um único objeto com nome, padrão e unidade
const produtos = {
  "I012277": {nome:"SACO PLASTICO 70 X 80 X 0,04 C/ 20CM DE SANFONA", padrao:"250", unidade:"UND"},
  "I012278": {nome:"SACO POLIEX. COL. 0,5 X 590 X 380MM MANAUS", padrao:"400", unidade:"UND"},
  "I012219": {nome:"BOBINA PICOTADA 35X45", padrao:"480", unidade:"MT"},
  "I012378": {nome:"SACO PLASTICO 70 X 20 X 0,04", padrao:"200", unidade:"MT"},
  "I005720": {nome:"BOBINA PICOTADA 40X60", padrao:"480", unidade:"MT"},
  "I012604": {nome:"FILME PROTETIVO (50 MICRAS) 140MMX300M", padrao:"300", unidade:"MT"},
  "I014062": {nome:"FILME DE PROTEÇÃO PELICULA 40 MICRAS 140X200MM", padrao:"200", unidade:"MT"},
  "I012279": {nome:"SEPARADOR PAPELÃO 260 X 360 MANAUS", padrao:"1000", unidade:"UND"},
  "I013797": {nome:"FOLHA SEPARADORA KRAFT (SLEP SHEET) 1110x1200MM", padrao:"250", unidade:"UND"},
  "I012714": {nome:"SEPARADOR PAPALELÃO 1100 X 1200 MANAUS", padrao:"1", unidade:"UND"},
  "I007237": {nome:"CAIXA DE PAPELÃO COD N 20", padrao:"1000", unidade:"UND"},
  "I012890": {nome:"FILME PROTETIVO (40 MICRAS) 110MMX200M", padrao:"200", unidade:"MT"},
  "I013394": {nome:"FILME PROTETIVO (40 MICRAS) 43MMX200M", padrao:"200", unidade:"MT"},
  "I000886": {nome:"FITA ADES 48MM X 45M - 3M", padrao:"45", unidade:"MT"},
  "I001215": {nome:"FITA ADES 25MM X 45M - 3M", padrao:"45", unidade:"MT"},
  "I012417": {nome:"PELICULA DE PLASTICO FILME STRETCH 500MM X 0,030MM X", padrao:"250", unidade:"MT"},
  "I013283": {nome:"LAMINA POLIEX 0,5 X 375 X 560MM", padrao:"1000", unidade:"UND"},
  "I002191": {nome:"PALLET DE PLASTICO", padrao:"1", unidade:"UND"},
  "I012218": {nome:"CAIXA KLT PRETA", padrao:"1", unidade:"UND"},
  "I012282": {nome:"CAIXA CONTAINER PRETA", padrao:"1", unidade:"UND"},
  "I014109": {nome:"FILME DE PROTEÇÃO PELICULA 40 MICRAS (170MMx 200Mt)", padrao:"200", unidade:"MT"},
  "I014243": {nome:"DIVISÓRIA DE PAPELÃO SC-450-C 630x970 (Manaus)", padrao:"50", unidade:"UND"},
  "I004333": {nome:"ETIQUETA 100 X 60 AA COUCHE 30GR 01 CARREIRA", padrao:"1000", unidade:"UND"},
  "I001630": {nome:"BOBINA RIBBON CERA 110 X 74M", padrao:"1", unidade:"UND"}
};

const selectProduto = $('#cod_produto_embalagem');
  const nomeProduto   = $('#nomeProduto');
  const padraoProduto = $('#padraoProduto');
  const undProduto    = $('#und');

  // popula select
  for (let codigo in produtos) {
    selectProduto.append(new Option(codigo, codigo));
  }

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
