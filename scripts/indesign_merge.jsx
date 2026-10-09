/* InDesign ExtendScript: silent Data Merge -> editable INDD.
 * Called from scripts/indesign_merge.py. Never changes the source template.
 */
(function () {
    var job = __JOB_JSON__;
    var savedInteractionLevel;
    var interactionLevelChanged = false;
    var stage = "startup";
    var doc = null;

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

    function errorDescription(err) {
        var parts = ["step=" + stage, "message=" + String(err)];
        try {
            if (err.number !== undefined) parts.push("number=" + err.number);
            if (err.line !== undefined) parts.push("line=" + err.line);
            if (err.fileName) parts.push("file=" + err.fileName);
        } catch (ignored) {}
        return parts.join("\n");
    }

    try {
        // InDesign application setting, not a document setting. Always restore
        // it, so the designer can see dialogs normally after automation ends.
        stage = "disable_dialogs";
        savedInteractionLevel = app.scriptPreferences.userInteractionLevel;
        app.scriptPreferences.userInteractionLevel = UserInteractionLevels.NEVER_INTERACT;
        interactionLevelChanged = true;

        stage = "validate_inputs";
        var sourceTemplate = new File(job.template);
        var csv = new File(job.csv);
        var target = new File(job.output);
        if (!sourceTemplate.exists) throw Error("INDD template missing");
        if (!csv.exists) throw Error("CSV file missing");
        if (target.exists) throw Error("Refusing to overwrite an existing merged INDD");

        stage = "open_template";
        doc = app.open(sourceTemplate, true);

        // A template may carry outdated linked graphics even if the new CSV
        // images all exist. Do not silently merge a layout with broken links.
        stage = "verify_template_links";
        var missingLinks = [];
        for (var linkIndex = 0; linkIndex < doc.links.length; linkIndex++) {
            var link = doc.links.item(linkIndex);
            if (link.status === LinkStatus.LINK_MISSING) {
                missingLinks.push(String(link.name));
            }
        }
        if (missingLinks.length > 0) {
            throw Error("Template has missing linked assets: "
                + missingLinks.slice(0, 12).join(", ")
                + (missingLinks.length > 12 ? " ..." : ""));
        }

        stage = "select_csv_data_source";
        // Reassert in case a previous operation temporarily changed the app pref.
        app.scriptPreferences.userInteractionLevel = UserInteractionLevels.NEVER_INTERACT;
        var dm = doc.dataMergeProperties;
        dm.selectDataSource(csv);

        stage = "validate_csv_fields";
        if (dm.dataMergeFields.length !== job.headers.length) {
            throw Error("CSV field count mismatch: received "
                        + dm.dataMergeFields.length + ", expected " + job.headers.length);
        }
        for (var i = 0; i < job.headers.length; i++) {
            var got = String(dm.dataMergeFields.item(i).fieldName);
            var expected = String(job.headers[i]);
            if (got.charAt(0) === "@") got = got.substring(1);
            if (expected.charAt(0) === "@") expected = expected.substring(1);
            if (got !== expected) {
                throw Error("Data Merge field mismatch at " + (i + 1)
                            + ": " + got + " != " + expected);
            }
        }

        stage = "validate_image_placeholders";
        if (doc.dataMergeImagePlaceholders.length < 6) {
            throw Error("Template has fewer than six image merge placeholders");
        }

        stage = "merge_all_records";
        doc.dataMergeOptions.createNewDocument = true;
        dm.dataMergePreferences.recordSelection = RecordSelection.ALL_RECORDS;
        app.scriptPreferences.userInteractionLevel = UserInteractionLevels.NEVER_INTERACT;
        dm.mergeRecords();

        stage = "save_merged_indd";
        var merged = app.activeDocument;
        if (!merged.isValid || merged.id === doc.id) {
            throw Error("InDesign failed to create a separate merged document");
        }
        merged.save(target);
        if (!target.exists) throw Error("Merged InDesign file did not save");
        // Keep the merged document open for the designer. Do not save the source.
        report("OK", target.fsName);
    } catch (error) {
        // A pre-existing modal dialog may block DoScript before this code even
        // starts; that case will be diagnosed on the Python/COM side instead.
        report("ERROR", errorDescription(error));
        throw error;
    } finally {
        if (interactionLevelChanged) {
            try {
                app.scriptPreferences.userInteractionLevel = savedInteractionLevel;
            } catch (restoreError) {
                // Do not obscure the original data-merge error.
                $.writeln("Could not restore userInteractionLevel: " + restoreError);
            }
        }
    }
}());
