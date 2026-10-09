/* Adobe InDesign ExtendScript: template + UTF-16 CSV -> editable merged INDD.
 * Placeholders are replaced by scripts/indesign_merge.py with escaped JS literals.
 * Never saves or overwrites the source template.
 */
(function () {
    var job = __JOB_JSON__;
    function report(status, message) {
        var f = new File(job.result);
        f.encoding = "UTF-8";
        if (!f.open("w")) {
            throw Error("Cannot write InDesign result file: " + job.result);
        }
        f.writeln(status);
        f.writeln(message);
        f.close();
    }
    try {
        var sourceTemplate = new File(job.template);
        var csv = new File(job.csv);
        var target = new File(job.output);
        if (!sourceTemplate.exists) throw Error("INDD template missing");
        if (!csv.exists) throw Error("CSV file missing");
        if (target.exists) throw Error("Refusing to overwrite an existing merged INDD");
        var doc = app.open(sourceTemplate, true);
        var dm = doc.dataMergeProperties;
        // Preserve existing placeholder frames from the original template.
        dm.selectDataSource(csv);

        if (dm.dataMergeFields.length !== job.headers.length) {
            throw Error("CSV field count mismatch: received "
                        + dm.dataMergeFields.length + ", expected " + job.headers.length);
        }
        for (var i = 0; i < job.headers.length; i++) {
            var got = String(dm.dataMergeFields.item(i).fieldName);
            var expected = String(job.headers[i]);
            // Adobe commonly omits the image prefix @ in fieldName.
            if (got.charAt(0) === "@") got = got.substring(1);
            if (expected.charAt(0) === "@") expected = expected.substring(1);
            if (got !== expected) {
                throw Error("Data Merge field mismatch at " + (i + 1) + ": " + got + " != " + expected);
            }
        }

        // Avoid silently generating blank pages when a wrong/empty INDD is used.
        // This product layout requires six image data-merge placeholders.
        if (doc.dataMergeImagePlaceholders.length < 6) {
            throw Error("Template has fewer than 6 image merge placeholders");
        }

        // Existing source template already contains the user-designed frames.
        // Merge ALL rows into a new editable document, not PDF or images.
        doc.dataMergeOptions.createNewDocument = true;
        dm.dataMergePreferences.recordSelection = RecordSelection.ALL_RECORDS;
        dm.mergeRecords();

        var merged = app.activeDocument;
        if (!merged.isValid || merged.id === doc.id) {
            throw Error("InDesign failed to create a separate merged document");
        }
        merged.save(target);
        if (!target.exists) throw Error("Merged InDesign file did not save");
        // Do NOT close or save the original template: users may have other open work.
        report("OK", target.fsName);
    } catch (error) {
        report("ERROR", String(error));
        // Also make the COM call report an error when possible.
        throw error;
    }
}());
