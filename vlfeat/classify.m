function classify(inputfile, outputfile)
    global model
    image = imread(inputfile);
    [label, score] = model.classify(model, image);
    fileID = fopen(outputfile,'w');
    fprintf(fileID,'%s\n',label);
    fprintf(fileID,'%f\n', score);
    fclose(fileID);
