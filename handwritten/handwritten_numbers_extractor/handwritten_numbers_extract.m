function numbers=handwritten_numbers_extract(imagename, outputfile)
    numbers=[];
    im = imread(imagename);
    level=graythresh(im);
    im_bw = im2bw(im,level);
    bwImage=~im_bw;

    if(length(size(im))==3)
       im = rgb2gray(im); 
    end
    
    %figure
    %imshow(bwImage)
    bwImage=clean_image(bwImage);

    %figure
    %imshow(bwImage)

    verticalProfile=mean(bwImage, 2);
    thresh=mean(verticalProfile)/200;

    %find the peaks of ink
    while true
        old=verticalProfile;
        verticalProfile = smooth(verticalProfile);
        if mean(abs(old-verticalProfile)) <= thresh
            break
        end
    end

    %find the gaps between the lines
    minVerticalProfile = max(verticalProfile) - verticalProfile;
    peaksmin = zeros(1,length(minVerticalProfile));
    [pks,locs] = findpeaks(minVerticalProfile);
    peaksmin(locs)=pks;

    dists = locs(2:end) - locs(1:end-1);
    dist_thresh = median(dists)/1.5;

    [peaks, locs]=clean_peaks(peaksmin, dist_thresh);

    peaks_im = bwImage;

    for loc=locs
        peaks_im(loc,:)=1;
    end

    if locs(1)-1>dist_thresh
        locs=[1 locs];
    end
    if length(minVerticalProfile)-locs(end)>dist_thresh
        locs=[locs length(minVerticalProfile)];
    end

    for li=1:length(locs)-1
        line = bwImage(locs(li):locs(li+1), :);
        line=clean_line(line, round(length(line)/200), round(length(line)/5), 1);
        %get_possible_chars(line);
%         size(im(locs(li):locs(li+1), :))
%         size(line)
        cline = im(locs(li):locs(li+1), :);% .* double(line==1);
%         cline = double(line==1);
        
        cc = bwconncomp(line);
        regions = regionprops(cc, 'BoundingBox');
        rects=zeros(length(regions),4);
        for j=1:length(regions)
            rects(j,:)=regions(j).BoundingBox;
        end
    
        %sort by x
        rects = sortrows(rects,1);   
        [num dummy]=size(rects);
        areas = zeros(1, num); 
        for j=1:num
           areas(1, j)=rects(j, 3)*rects(j,4);
        end

%         median_area = median(areas);
    
        nums = zeros(1, num);
        scores = zeros(1, num);
        for j=1:num           
           if rects(j,3)< 1.2*rects(j,4) && areas(1,j)>100 % && areas(1,j)>median_area/5 
%                rectangle('Position', rects(j,:),'EdgeColor','r','LineWidth',2 )
%             imfilename=sprintf('%d-%d.png', li, j);
%             imwrite(cline(max(floor(rects(j, 2)), 1):max(floor(rects(j, 2)+rects(j, 4)), 1), max(floor(rects(j, 1)), 1):max(floor(rects(j, 1)+rects(j, 3)), 1)), imfilename);
%             [label, score]=handwritten_digit_classify(imfilename)
%             fileID = fopen(sprintf('%d-%d.txt', li, j),'w');
%             fprintf(fileID,'%d\n',label);
%             fprintf(fileID,'%f\n', score);
%             fclose(fileID);
            imfilename='char.png';
            imwrite(cline(max(floor(rects(j, 2)), 1):max(floor(rects(j, 2)+rects(j, 4)), 1), max(floor(rects(j, 1)), 1):max(floor(rects(j, 1)+rects(j, 3)), 1)), imfilename);
            [label, score]=handwritten_digit_classify(imfilename);
            nums(1, j)=label;
            scores(1,j)=score;
            delete(imfilename);
           end
        end
        %nums = nums .* (scores>0.8);
        
        started=false;
        currnum=0;
        
        for j=1:num
           %if nums(1, j)~=0
           if scores(1, j)>=0.8
               started=true;
              currnum = (currnum*10)+nums(1,j);
           elseif started==true
               numbers(end+1)=currnum;
               currnum=0;
               started=false;
           end
        end
        
        
    end

    fileID = fopen(outputfile,'w');
    for n=numbers
    	fprintf(fileID,'%d\n', n);
    end
    fclose(fileID);


end

function chars=get_possible_chars(line)
    figure
    subplot(5, 1, 1);
    imshow(line);
    [width height] = size(line);
    horizontalProfile=mean(line, 1);
    subplot(5, 1, 2);
    plot(horizontalProfile);
    divs = (horizontalProfile==0).*height;
    
    subplot(5, 1, 3);
    imshow(line); hold on

    plot(divs,'LineWidth',2,'Color','red');
    hold off

    
    cc = bwconncomp(line);
    regions = regionprops(cc, 'BoundingBox');
    rects=zeros(length(regions),4);
    for i=1:length(regions)
        rects(i,:)=regions(i).BoundingBox;
    end
    
    
    subplot(5, 1, 4);
    imshow(line); hold on


    %sort by x
    rects = sortrows(rects,1);   
    [num dummy]=size(rects);
    areas = zeros(1, num); 
    for i=1:num
       rectangle('Position', rects(i,:),'EdgeColor','r','LineWidth',2 )
       areas(1, i)=rects(i, 3)*rects(i,4);
    end
    hold off

    median_area = median(areas);
    subplot(5, 1, 5);
    imshow(line); hold on
    for i=1:num
       if areas(1, i)>median_area/5;
           rectangle('Position', rects(i,:),'EdgeColor','r','LineWidth',2 )
       end
    end
    hold off
    chars=[];
end

function img=clean_line(oimg, fillgap, minlen, linethickness)
    img=oimg;
    [H,T,R] = hough(img);
    P  = houghpeaks(H,5);
    lines = houghlines(img,T,R,P,'FillGap',fillgap,'MinLength', minlen);
    [maxw maxh] = size(oimg);
    for k = 1:length(lines)
       if isfield(lines(k), 'point1')
           x0=min(lines(k).point1(1),lines(k).point2(1));
           y0=max(0, min(lines(k).point1(2),lines(k).point2(2))-linethickness);
           x1=max(lines(k).point1(1),lines(k).point2(1));
           y1=min(max(lines(k).point1(2),lines(k).point2(2))+linethickness, maxh);
           img(y0:y1,x0:x1)=0;
           
       end
    end

    ccs = bwconncomp(img);
    plist=ccs.PixelIdxList;
    sizes=zeros(1, length(plist));
    for i=1:length(plist)
        cc=plist(i);
        pl=cc{1};
        sizes(i)=length(pl); 
    end
    if round(median(sizes)/10)>1
        img=bwareaopen(img, round(median(sizes)/10));
    end
end

function cimg=clean_image(img)
    %get connected components
    ccs = bwconncomp(img);
    plist=ccs.PixelIdxList;
    sizes=zeros(1, length(plist));
    for i=1:length(plist)
        cc=plist(i);
        pl=cc{1};
        sizes(i)=length(pl); 
    end

    if mean(sizes) > 5 * median(sizes)
        cimg=bwareaopen(img, round(median(sizes)/2));
    else
        cimg=bwareaopen(img, round(median(sizes)/10));
    end
end


function [peaks, locs]=clean_peaks(peaks, dist_thresh)
    while true
        locs = find(peaks);
        dists = locs(2:end) - locs(1:end-1);
        for i=1:length(locs)-1
           if dists(i)<dist_thresh
               if peaks(locs(i))>peaks(locs(i+1))
                   peaks(locs(i+1))=0;
               else
                   peaks(locs(i))=0;
               end
               break 
           end
        end
        if i == length(locs)-1
           break
        end
    end
end
