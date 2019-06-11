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
  cbs.c = function(id) {
    return document.getElementById(id).checked
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
      if (data === null) return
      for (let [cmd, target_id, html] of data) {
        if (cmd === UPDATE) {
          var el1 = document.getElementById("conent")
          var el2 = document.getElementById("content2")
          el2.innerHTML = html
          morphdom(el1, el2, {childrenOnly: true})
          el2.innerHTML = ""
        } else {
          throw("Unknown command: " + cmd)
        }
      }
    }
  })
}

