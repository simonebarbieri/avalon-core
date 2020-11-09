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

function getItems(comps, folders, footages){
    /**
     * Returns JSON representation of compositions and
     * if 'collectLayers' then layers in comps too.
     * 
     * Args:
     *     comps (bool): return selected compositions
     *     folders (bool): return folders
     *     footages (bool): return FootageItem
     * Returns:
     *     (list) of JSON items
     */    
    var items = []
    for (i = 1; i <= app.project.items.length; ++i){
        var item = app.project.items[i];
        if (!item){
            continue;
        }
        var ret = _getItem(item, comps, folders, footages);
        if (ret){
            items.push(ret);
        }
    }
    return '[' + items.join() + ']';

}

function getSelectedItems(comps, folders, footages){
    /**
     * Returns list of selected items from Project menu
     * 
     * Args:
     *     comps (bool): return selected compositions
     *     folders (bool): return folders
     *     footages (bool): return FootageItem
     * Returns:
     *     (list) of JSON items
     */    
    var items = []
    for (i = 0; i < app.project.selection.length; ++i){
        var item = app.project.selection[i];
        if (!item){
            continue;
        }
        var ret = _getItem(item, comps, folders, footages);
        if (ret){
            items.push(ret);
        }
    }
    return '[' + items.join() + ']';
}

function _getItem(item, comps, folders, footages){
    /**
     * Auxiliary function as project items and selections 
     * are indexed in different way :/
     * Refactor 
     */
    var item_type = '';
    if (item instanceof FolderItem){
        item_type = 'folder';
        if (!folders){
            return null;
        }
    }
    if (item instanceof FootageItem){
        item_type = 'footage';
        if (!footages){
            return null;
        }
    }
    if (item instanceof CompItem){
        item_type = 'comp';
        if (!comps){
            return null;
        }
    }
        
    var item = {"name": item.name,
                "id": item.id,
                "type": item_type};
    return JSON.stringify(item);
}

function importFile(path, item_name, import_options){
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
    var ret = {};
    try{
        import_options = JSON.parse(import_options);
    } catch (e){
        alert("Couldn't parse import options " + import_options);
    }

    app.beginUndoGroup("Import File");
    fp = new File(path);
    if (fp.exists){
        try { 
            im_opt = new ImportOptions(fp);
            importAsType = import_options["ImportAsType"];

            if ('ImportAsType' in import_options){ // refactor
                if (importAsType.indexOf('COMP') > 0){
                    im_opt.importAs = ImportAsType.COMP;
                }
                if (importAsType.indexOf('FOOTAGE') > 0){
                    im_opt.importAs = ImportAsType.FOOTAGE;
                }
                if (importAsType.indexOf('COMP_CROPPED_LAYERS') > 0){
                    im_opt.importAs = ImportAsType.COMP_CROPPED_LAYERS;
                }
                if (importAsType.indexOf('PROJECT') > 0){
                    im_opt.importAs = ImportAsType.PROJECT;
                }  
                             
            }
            if ('sequence' in import_options){
                im_opt.sequence = true;
            }
            
            comp = app.project.importFile(im_opt);

            if (app.project.selection.length >= 2){
                for (i = 0; i < app.project.selection.length; ++i){
                    var item = app.project.selection[i];
                    if (item instanceof FolderItem){
                        comp.parentFolder = item;
                    }
                }
            }
        } catch (error) {
            $.writeln(error);
            alert(error.toString() + importOptions.file.fsName, scriptName);
        } finally {
            fp.close();
        }
    }else{
        alert("File " + path + " doesn't exist.");
    }
    if (comp){
        comp.name = item_name;
        comp.label = 9; // Green
        $.writeln(comp.id);
        ret = {"name": comp.name, "id": comp.id}
    }
    app.endUndoGroup();

    return JSON.stringify(ret);
}

function setLabelColor(item_id, color_idx){
    /**
     * Set item_id label to 'color_idx' color
     * Args:
     *     item_id (int): item id
     *     color_idx (int): 0-16 index from Label
     */
    for (var i = app.project.numItems; i >= 1; i--) {
        var curItem = app.project.item(i);
        if (curItem.id == item_id){
            curItem.label = color_idx;
            break;
        }
    }
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

// // var img = 'c:\\projects\\petr_test\\assets\\locations\\Jungle\\publish\\image\\imageBG\\v013\\petr_test_Jungle_imageBG_v013.jpg';
//  var psd = 'c:\\projects\\petr_test\\assets\\locations\\Jungle\\publish\\workfile\\workfileArt\\v013\\petr_test_Jungle_workfileArt_v013.psd';
//var mov = 'c:\\Users\\petrk\\Downloads\\Samples\\sample_iTunes.mov';
// // var wav = 'c:\\Users\\petrk\\Downloads\\Samples\\africa-toto.wav';

// var inop = JSON.stringify({sequence: true});
// $.writeln(inop);
// importFile(mov, "mov", inop); // should be able to import PSD and all its layers
//importFile(mov, "new_wav", '{}');
// $.writeln(app.project.selection);
// for (i = 1; i <= app.project.selection.length; ++i){
//     var sel = app.project.selection[i];
//     $.writeln(sel);
//     $.writeln(app.project.selection[0] instanceof FolderItem);
//}
//$.writeln(getItems(true, false, false));
//importFile(mov, "new_wav", "{}");
// var inop = JSON.stringify({sequence: true});
// var seq = "C:/projects/petr_test/assets/locations/Jungle/publish/render/reviewArt/v003/petr_test_Jungle_reviewArt_v003.0001.jpg";
// importFile(seq, "new_wav", inop);













