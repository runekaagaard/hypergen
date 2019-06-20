"use strict"
// We are aiming for IE6 support here, hence the oldschool js.


var H = (function() {
  // Shims
  if (typeof Array.isArray === 'undefined') {
    Array.isArray = function(obj) {
      return Object.prototype.toString.call(obj) === '[object Array]';
    }
  };

  // Callback handlers.
  console.log("RECEIVING", arguments)
  var cbs = {}
  cbs.i = function(id) { return function() {
    return parseInt($("#" + id).val())
  }}
  cbs.f = function(id) { return function() {
    return parseFloat($("#" + id).val())
  }}
  cbs.s = function(id) { return function() {
    return "" + $("#" + id).val()
  }}
  cbs.c = function(id) { return function() {
    return document.getElementById(id).checked
  }}

  function parseArgs(args, data) {
    for (var i=0; i<args.length; i++) {
      var x = args[i]
      if (typeof x === "function") {
        data.push(x())  
      } else if (Array.isArray(x)) {
        var tmp = []
        parseArgs(x, tmp)
        data.push(tmp)
      } else {
        data.push(x)
      }
    }
  }
  
  function cb() {
    var
      UPDATE = 1,
      url = arguments[0],
      args = [],
      data = []

    for (var i=1; i<arguments.length; i++) {
      args.push(arguments[i])
    }
    
    parseArgs(args, data)
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
        for (var i=0; i<data.length; i++) {
          var
            item = data[i],
            cmd = item[0],
            target_id = item[1],
            html = item[2]
          if (cmd === UPDATE) {
            morphdom(
              document.getElementById(target_id),
              "<div>" + "</div>",
              {childrenOnly: true}
            )
            morphdom(
              document.getElementById(target_id),
              "<div>" + html + "</div>",
              {childrenOnly: true}
            )
          } else {
            throw("Unknown command: " + cmd)
          }
        }
      }
    })
  }

  return {
    cb: cb,
    cbs: cbs,
  }
})()
