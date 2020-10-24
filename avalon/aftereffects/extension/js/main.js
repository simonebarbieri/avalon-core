/*jslint vars: true, plusplus: true, devel: true, nomen: true, regexp: true, indent: 4, maxerr: 50 */
/*global $, window, location, CSInterface, SystemPath, themeManager*/


var csInterface = new CSInterface();
    
log.warn("script start");

WSRPC.DEBUG = false;
WSRPC.TRACE = false;

function runEvalScript(script) {
    // because of asynchronous nature of functions in jsx
    // this waits for response
    return new Promise(function(resolve, reject){
        csInterface.evalScript(script, resolve);
    });
}

// get websocket server url from environment value
async function startUp(url){
    promis = runEvalScript("getEnv('" + url + "')");

    var res = await promis; 
    log.warn("res: " + res);
    // run rest only after resolved promise
    main(res);
}

function main(websocket_url){
  // creates connection to 'websocket_url', registers routes      
  var default_url = 'ws://localhost:8099/ws/';

  if  (websocket_url == ''){
       websocket_url = default_url;
  }
  RPC = new WSRPC(websocket_url, 5000); // spin connection

  RPC.connect();

  log.warn("connected"); 
}


function EscapeStringForJSX(str){
    // Replaces:
    //  \ with \\
    //  ' with \'
    //  " with \"
    // See: https://stackoverflow.com/a/3967927/5285364
    return str.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '\\"');
}



/** main entry point **/
startUp("WEBSOCKET_URL");

var escapedPath = EscapeStringForJSX("C:\Users\petrk\Documents\TestProject.aep");
runEvalScript("fileOpen('" + escapedPath +"')")
                  .then(function(result){
                      log.warn("open: " + result);
                      return result;
                  });

runEvalScript("getHeadline()")
                  .then(function(result){
                      log.warn("getHeadline: " + result);
                      return result;
                  });




(function () {
    'use strict';

    var csInterface = new CSInterface();
    
    
    function init() {
                
        themeManager.init();
                
        $("#btn_test").click(function () {
            csInterface.evalScript('sayHello()');
        });
    }
        
    init();

}());
    
