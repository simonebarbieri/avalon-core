/*jslint vars: true, plusplus: true, devel: true, nomen: true, regexp: true,
indent: 4, maxerr: 50 */
/*global $, Folder*/
#include "../js/libs/json.js";

app.preferences.savePrefAsBool("General Section", "Show Welcome Screen", false) ;



function sayHello(){
    alert("hello from ExtendScript");
}

function getEnv(variable){
    return $.getenv(variable);
}

function getMetadata(){
    /**
     *  Returns payload in 'Label' field of project's metadata
     * 
     **/
    if (ExternalObject.AdobeXMPScript === undefined){
        ExternalObject.AdobeXMPScript =
            new ExternalObject('lib:AdobeXMPScript');
    }
    
    var proj = app.project;
    var meta = new XMPMeta(app.project.xmpPacket);
    var schemaNS = XMPMeta.getNamespaceURI("xmp");
    var label = "xmp:Label";

    if (meta.doesPropertyExist(schemaNS, label)){
        var prop = meta.getProperty(schemaNS, label);
        return prop.value;
    }

    return null;

}

function imprint(payload){
    /**
     * Stores payload in 'Label' field of project's metadata
     * 
     * Args:
     *     payload (string): json content
     */
    if (ExternalObject.AdobeXMPScript === undefined){
        ExternalObject.AdobeXMPScript =
            new ExternalObject('lib:AdobeXMPScript');
    }
    
    var proj = app.project;
    var meta = new XMPMeta(app.project.xmpPacket);
    var schemaNS = XMPMeta.getNamespaceURI("xmp");
    var label = "xmp:Label";

    meta.setProperty(schemaNS, label, payload);
    
    app.project.xmpPacket = meta.serialize();
}


function fileOpen(path){
    /**
     * Opens (project) file on 'path'
     */
    fp = new File(path);
    return app.open(fp);
}

function getActiveDocumentName(){
    /**
     *   Returns file name of active document
     * */
    var file = app.project.file;

    if (file){
        return file.name;   
    }

    return null;
}

function getActiveDocumentFullName(){
    /**
     *   Returns absolute path to current project
     * */
    var file = app.project.file;

    if (file){
        var f = new File(file.fullName);
        var path = f.fsName;
        f.close();

        return path;   
    }

    return null;
}

function getItems(collectLayers){
    /**
     * Returns JSON representation of compositions and
     * if 'collectLayers' then layers in comps too.
     * 
     * Args:
     *     collectLayers (bool): return layers too
     * Returns:
     *    (array) of JSON
     */
    var items = [];
    //loop through comps and layers: 
    for (i = 1; i <= app.project.numItems; ++i) {  
        var currentComp = app.project.item(i);
        var item = {"name": currentComp.name, 
                    "id": currentComp.id,
                    "type": "comp"};
        var parent_id = currentComp.id; 
        items.push(JSON.stringify(item));
        
        if (collectLayers && currentComp instanceof CompItem) { 
            var layers = currentComp.layers;
            for (j = 1; j <= layers.length; ++j){
                var layer = layers[j];
                var item = {"name": layer.name,
                            "id": layer.id,
                            "parrent_id": parent_id,
                            "type": "layer"};
                items.push(JSON.stringify(item));
            }          
        }
    }
    return '[' + items.join() + ']';
}

function importFile(path, item_name){
    /**
     * Imports file (image tested for now) as a FootageItem.
     * Creates new composition
     * 
     * Args:
     *    path (string): absolute path to image file
     *    item_name (string): label for composition
     * Returns:
     *    JSON {name, id}
     */
    var comp;
    var ret = {}
    app.beginUndoGroup("Import File");
    fp = new File(path);
    if (fp.exists){
        try { 
            comp = app.project.importFile(new ImportOptions(fp));
        } catch (error) {
            alert(error.toString() + importOptions.file.fsName, scriptName);
        } finally {
            fp.close();
        }
    }
    if (comp){
        comp.name = item_name;
        $.writeln(comp.id);
        ret = {"name": comp.name, "id": comp.id}
    }
    app.endUndoGroup();

    return JSON.stringify(ret);
}

function replaceItem(comp_id, path, item_name){
    /**
     * Replaces loaded file with new file and updates name
     * 
     * Args:
     *    comp_id (int): id of composition, not a index!
     *    path (string): absolute path to new file
     *    item_name (string): new composition name
     */
    app.beginUndoGroup("Replace File");
    
    fp = new File(path);
    for (var i = app.project.numItems; i >= 1; i--) {
        var curItem = app.project.item(i);
        if (curItem.id == comp_id){
            try{
                curItem.replace(fp);
                curItem.name = item_name;
            } catch (error) {
                alert(error.toString() + path, scriptName);
            } finally {
                fp.close();
            }
            break;
        } 
    }
    app.endUndoGroup();
}

function deleteItem(comp_id){
    /**
     * Deletes by 'comp_id', which is not index of 'items'
     */
    for (var i = app.project.numItems; i >= 1; i--) {
        var curItem = app.project.item(i);
        if (curItem.id == comp_id){
            curItem.remove();
            break;
        } 
    }  
}

function save(){
    /**
     * Saves current project
     */
    return app.project.save();  //TODO path is wrong, File instead
}

function saveAs(path){
    /**
     *   Saves current project as 'path'
     * */
    return app.project.save(fp = new File(path));
}

var img = 'c:\\projects\\petr_test\\assets\\locations\\Jungle\\publish\\image\\imageBG\\v013\\petr_test_Jungle_imageBG_v013.jpg';
var psd = 'c:\\projects\\petr_test\\assets\\locations\\Jungle\\publish\\workfile\\workfileArt\\v013\\petr_test_Jungle_workfileArt_v013.psd';

//importFile(psd, "new_psd"); // should be able to import PSD and all its layers














