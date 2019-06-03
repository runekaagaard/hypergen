const UPDATE = 1;

function H(url, ...args) {
  console.log("GETTING", args)
  const data = args.map(x => {
    try {
      if (x.length !== 2 || x[0] !== "_H") throw("")
      return parseInt($("#" + x[1]).val())
    } catch(err) {
      console.log(err)
      return x
    }
  })
  console.log("SHIPPING", data)
  $.ajax({
    url: url,
    type: 'POST',
    data: JSON.stringify(data),
    contentType: 'application/json; charset=utf-8',
    dataType: 'json',
    success: function(data) {
      for (let [cmd, target_id, html] of data) {
        if (cmd === UPDATE) {
          $("#" + target_id).html(html)
        } else {
          throw(`Unknown command: $(cmd).`)
        }
      }
    }
  })
}
