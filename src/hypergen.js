"use strict"
// We are aiming for IE6 support here, hence the oldschool js.


function H() {
  console.log("RECEIVING", arguments)
  var
    UPDATE = 1,
    cbs = {},
    url = arguments[0],
    data = []
  
  cbs.i = function(id) {
    return parseInt($("#" + id).val())
  }
  cbs.f = function(id) {
    return parseFloat($("#" + id).val())
  }
  cbs.s = function(id) {
    return "" + $("#" + id).val()
  }
  
  for (var i=1; i<arguments.length; i++) {
    var x = arguments[i]
    try {
      if (x.length === 3 && x[0] === "H_") {
        data.push(cbs[x[1]](x[2]))
      } else {
        data.push(x)
      }
    } catch(err) {
      console.log(err)
      data.push(x)
    }
  }
  
  console.log("REQUEST", data)
  $.ajax({
    url: url,
    type: 'POST',
    data: JSON.stringify(data),
    contentType: 'application/json; charset=utf-8',
    dataType: 'json',
    success: function(data) {
      console.log("RESPONSE", data)
      console.log("")
      for (let [cmd, target_id, html] of data) {
        if (cmd === UPDATE) {
          $("#" + target_id).html(html)
        } else {
          throw("Unknown command: " + cmd)
        }
      }
    }
  })
}

