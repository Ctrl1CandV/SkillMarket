// 两个页面共用的数据层：示例数据 + 浏览器本地存储里的改动（新订单、已取、取消）。
(function () {
  const KEY = 'xiangkou-bakery.v1';
  const seed = window.BAKERY_SEED;
  const load = () => { try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { return {}; } };
  const save = (s) => { try { localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) { /* 存不了就只在本页生效 */ } };
  let state = Object.assign({ added: [], status: {}, me: null }, load());

  const productById = Object.fromEntries(seed.products.map(p => [p.id, p]));
  const slotById = Object.fromEntries(seed.slots.map(s => [s.id, s]));

  function orders() {
    return seed.orders.concat(state.added).map(o => Object.assign({}, o, state.status[o.id] ? { status: state.status[o.id] } : null));
  }
  function live() { return orders().filter(o => o.status !== 'cancelled'); }
  function reserved(productId) {
    return live().reduce((n, o) => n + o.items.filter(i => i.product === productId).reduce((a, i) => a + i.qty, 0), 0);
  }
  function remaining(productId) { return Math.max(0, productById[productId].daily_limit - reserved(productId)); }
  function total(order) { return order.items.reduce((n, i) => n + i.qty * productById[i.product].price, 0); }
  function setStatus(id, status) { state.status[id] = status; save(state); }
  function addOrder(draft) {
    const n = seed.orders.length + state.added.length + 1;
    const order = Object.assign({ id: '1113-' + String(n).padStart(3, '0'), status: 'reserved', created_at: new Date().toISOString() }, draft);
    state.added.push(order); state.me = { id: order.id, name: order.name, phone: order.phone }; save(state);
    return order;
  }
  function mine() { return state.me ? orders().find(o => o.id === state.me.id) || null : null; }
  function remembered() { return state.me; }
  function reset() { state = { added: [], status: {}, me: null }; save(state); }

  // 示例时间：数据是 11 月 13 日取货的订单，页面按“示例时间”演示；网址加 ?now=HH:MM 可以换时间。
  function demoClock(defaultTime) {
    const m = /[?&]now=(\d{1,2})[:.](\d{2})/.exec(location.search);
    const [h, min] = m ? [+m[1], +m[2]] : defaultTime.split(':').map(Number);
    return { h, min, minutes: h * 60 + min, label: String(h).padStart(2, '0') + ':' + String(min).padStart(2, '0') };
  }
  const SLOT_HOURS = { morning: [7 * 60, 9 * 60], noon: [11 * 60, 13 * 60], evening: [17 * 60, 19 * 60] };

  window.Bakery = { shop: seed.shop, products: seed.products, slots: seed.slots, productById, slotById, SLOT_HOURS,
    orders, live, reserved, remaining, total, setStatus, addOrder, mine, remembered, reset, demoClock };
  window.addEventListener('storage', (e) => { if (e.key === KEY) { state = Object.assign({ added: [], status: {}, me: null }, load()); window.dispatchEvent(new Event('bakery:changed')); } });
})();
