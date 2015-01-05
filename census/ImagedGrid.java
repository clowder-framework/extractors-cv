package edu.illinois.ncsa.medici.census;

import kgm.image.*;
import kgm.matrix.*;
import kgm.utility.*;
import ncsa.im2learn.core.datatype.*;
import ncsa.im2learn.core.io.*;

import java.awt.image.*;
import java.io.*;
import java.util.*;

import org.apache.log4j.*;
import org.opencv.core.*;
import org.opencv.highgui.*;
import org.opencv.imgproc.*;
import org.opencv.features2d.*;


/**
 * An interface to information contained within an image of a form containing data within a grid of cells.
 * @author Kenton McHenry
 */
public class ImagedGrid
{
	
	  static{ 
		  System.loadLibrary("opencv_java2410"); 
//		  System.loadLibrary(Core.NATIVE_LIBRARY_NAME);
		  System.out.println( "OpenCV Core version "+ Core.VERSION);
	  }

	
	private int[][] image_rgb;
	private double[] image_g;
	private int width, height;
	private double threshold;
	public boolean SHOW_TEMPLATE_ALIGNMENT = true;
	public boolean SAVE_ROTATED_IMAGE = false;
	
	/**
	 * A simple structure that represents a cell location within an image as a transformation of a unit square at the origin.
	 */
	public static class CellLocation
	{
		public double[][] M;
		
		public CellLocation() {}
		
		/**
		 * Class constructor.
		 * @param M the transformation matrix for the cell location
		 */
		public CellLocation(double[][] M)
		{
			this.M = M;
		}
		
		/**
		 * Set the location based on a given scale and translation.
		 * @param sx the scale in the x direction
		 * @param sy the scale in the y direction
		 * @param tx the translation in the x direction
		 * @param ty the translation in the y direction
		 */
		public void set(double sx, double sy, double tx, double ty)
		{
			M = MatrixUtility.mtimes(MatrixUtility.translate(tx, ty), MatrixUtility.scale(sx, sy));
			MatrixUtility.println(M);
		}
		
		/**
		 * Get the cell image.
		 * @param image the full image
		 * @return the cell image
		 */
		public int[][] get(int[][] image)
		{
			int height = image.length;
			int width = image[0].length;			
			double[] p0 = MatrixUtility.mtimes(M, new double[]{-0.5, 0.5, 1});
			double[] p1 = MatrixUtility.mtimes(M, new double[]{0.5, 0.5, 1});
			double[] p2 = MatrixUtility.mtimes(M, new double[]{0.5, -0.5, 1});
			double[] p3 = MatrixUtility.mtimes(M, new double[]{-0.5, -0.5, 1});
			double[] p;
			int w = (int)Math.round(MatrixUtility.distance(p0, p1));
			int h = (int)Math.round(MatrixUtility.distance(p0, p3));
			int[][] cell = new int[h][w];
			int xi, yi;
			
			for(int x=0; x<w; x++){
				for(int y=0; y<h; y++){
					p = MatrixUtility.mtimes(M, new double[]{((double)x)/w-0.5, ((double)y)/h-0.5, 1});
					xi = (int)Math.round(p[0]);
					yi = (int)Math.round(p[1]);
					
					if(xi>=0 && xi<width && yi>=0 && yi<height){
						cell[y][x] = image[yi][xi];
					}
				}
			}
			
			return cell;
		}
	}
	
	/**
	 * Class constructor.
	 * @param filename the name of the image to load
	 */
	public ImagedGrid(String filename)
	{
		int[][] image = null;
		
		if(false){
			image = ImageUtility.load(filename);	
		}else{
			image = load(filename);
		}
		
		setImage(image);
	}
	
	/**
	 * Class constructor.
	 * @param image a color image
	 */
	public ImagedGrid(int[][] image)
	{
		setImage(image);
	}
	
	
	/**
	 * Class constructor.
	 * @param image a color image
	 * @param threshold the threshold to be used in the binarization process
	 */
	public ImagedGrid(int[][] image, double threshold)
	{
		setImage(image, threshold);
	}
	
	
	/**
	 * Class constructor.
	 * @param image a grayscale image
	 * @param w the width of the image
	 * @param h the height of the image
	 */
	public ImagedGrid(double[] image, int w, int h)
	{
		setImage(ImageUtility.to2D(ImageUtility.g2argb(image, w, h), w, h));
	}
	
	/**
	 * Set the image.
	 * @param image a color image
	 */
	public void setImage(int[][] image)
	{
		image_rgb = image;
		image_g = ImageUtility.argb2g(image_rgb);
		width = image_rgb[0].length;
		height = image_rgb.length;		
		threshold = findBinarizationTreshold(image_g, width, height);
		binarize(threshold);
//		binarize();
	}


	
	/**
	 * Set the image.
	 * @param image a color image
	 * @param thresh the threshold to be used in the binarization process
	 */
	public void setImage(int[][] image, double thresh)
	{
		image_rgb = image;
		image_g = ImageUtility.argb2g(image_rgb);
		width = image_rgb[0].length;
		height = image_rgb.length;				
		threshold = thresh;
		binarize(thresh);
	}
	
	
	/**
	 * Get the color image.
	 * @return the color image
	 */
	public int[][] getColorImage()
	{
		return image_rgb;
	}

	/**
	 * Get the associated grayscale image.
	 * @return the grayscale image
	 */
	public double[] getGrayscaleImage()
	{
		return image_g;
	}

	/**
	 * Get the image width.
	 * @return the image width
	 */
	public int getWidth()
	{
		return width;
	}

	/**
	 * Get the image height.
	 * @return the image height
	 */
	public int getHeight()
	{
		return height;
	}

	/**
	 * Display the image.
	 */
	public void show()
	{
		ImageViewer viewer = new ImageViewer(image_rgb, width, height, 1200, "Form");
		viewer.add(image_g, width, height, true);
	}

	/**
	 * Crop the image by imposing the given margin.
	 * @param margin the margin to crop out
	 */
	public void crop(int margin)
	{
		image_rgb = ImageUtility.crop(image_rgb, margin, margin, width-2*margin, height-2*margin);
		image_g = ImageUtility.crop(image_g, width, height, margin, margin, width-2*margin, height-2*margin);
		width = (width-2*margin)-margin+1;
		height = (height-2*margin)-margin+1;
	}
	
	/**
	 * Binarize the grayscale image.
	 */
	public void binarize()
	{
		for(int i=0; i<image_g.length; i++){
			if(image_g[i] < 0.7){//0.5
				image_g[i] = 1;
			}else{
				image_g[i] = 0;
			}
		}
	}

	public double findBinarizationTreshold(double[] image_g, int width, int height){
        int x0,  y0;
       
        double total=0;
        for(int t=0;t<image_g.length;t++)
            total+=image_g[t];
        total=total/image_g.length;

        double middle=0;//, m_count=0;
        x0=width/2;
        y0=height/2;
        if(x0<101 || y0<101){
            return total;
        }
        else{
            for(int x=-100;x<=100;x++){// && (x0+x>=0) && (x0+x<width)
                for(int y=-100;y<=100;y++){// && (y0+y>=0) && (y0+y<height)
                    middle+=image_g[(y0+y)*width+(x0+x)];
                }
            }
            middle=middle/40401;//201*201
        }
//        System.out.println("height: "+height+" average color: "+total+",  middle color: "+middle);
        if(total<0.5) return total;
        if(middle>0.9) return (middle+total)/2;
        return middle;
    }
	
	/**
	 * Binarize the grayscale image.
	 */
	public void binarize(double thresh)
	{
		for(int i=0; i<image_g.length; i++){
			if(image_g[i] < thresh){
				image_g[i] = 1;
			}else{
				image_g[i] = 0;
			}
		}
	}

	
	/**
	 * Scale the image.
	 * @param scale the scale factor
	 */
	public void scale(double scale)
	{
		image_rgb = ImageUtility.resize(image_rgb, scale);
		image_g = MatrixUtility.to1D(ImageUtility.resize(MatrixUtility.to2D(height, width, image_g), scale));
		height = image_rgb.length;
		width = image_rgb[0].length;		
	}

	/**
	 * Thin the grid lines in the grayscale image.
	 */
	public void thin()
	{
		thin(image_g, width, height);
	}
	
	/**
	 * Thin the grid lines in the grayscale image.
	 */
	public void hilditch()
	{
		ImageUtility.hilditch(image_g, width, height);
	}
	
	/**
	 * Thicken the grid lines in the grayscale image.
	 */
	public void thicken()
	{
		image_g = ImageUtility.thicken(image_g, width, height);
	}



	/**
	 * Get the rotation of a scanned grid (assumes rotated about center).
	 * @return the angle of rotation
	 */
	public double getRotation()
	{
//		ImageUtility.save("tmp/output_lines.jpg", ImageUtility.to2D(this.image_g, width, height));
		
		File fimg=null;
		try {
			fimg = File.createTempFile("cellgrid", ".jpg");
//			System.out.println(fimg.getAbsolutePath());
			ImageUtility.save(fimg.getAbsolutePath(), image_rgb);
		} catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
		
		//load image as OpenCV Mat
		Mat img = Highgui.imread(fimg.getAbsolutePath());
				
		if(fimg.exists()){
			fimg.delete();
		}
		
		//threshold images to get only the ink
		Mat bw = new Mat();
		Imgproc.threshold(img, bw, 127, 255, Imgproc.ADAPTIVE_THRESH_GAUSSIAN_C);//(gray, bw, 0, 0, Imgproc.THRESH_OTSU);
		
		//transform image in grayscale
		Mat bw_gray = new Mat();
		Imgproc.cvtColor(bw, bw_gray, Imgproc.COLOR_BGR2GRAY);
		
		//create edge map
		Mat edges = new Mat();
		int lowThreshold = 50;
		int ratio = 3;
		Imgproc.Canny(bw_gray, edges, lowThreshold, lowThreshold * ratio);
		

		//compute hough lines
		Mat lines = new Mat();		
		int min_line_length=(int)Math.round(0.25*img.width())+1;
		int max_line_gap=(int)Math.round(0.025*img.width())+1;//min_line_length/10;//100
		int min_line_votes = (int)Math.round(0.1*img.width())+1;//1000;//1000

		double theta_resolution=1;

		Imgproc.HoughLinesP(edges, lines, 10, theta_resolution*Math.PI/180, min_line_votes, min_line_length, max_line_gap);
		

		//add lines to histogram
		Histogram<Double> histogram = new Histogram<Double>(Histogram.createDoubleBins(0, 1, 180));
		double theta;

		for(int i = 0; i < lines.cols(); i++) {
//			System.out.println("Col "+i+":");
			double[] val = lines.get(0, i);
			
//        	Core.line(img, new Point(val[0], val[1]), new Point(val[2], val[3]), new Scalar(0, 0, 255), 5);
			
//        	System.out.println("ANG = "+(Math.atan((val[3]-val[1])/(val[2]-val[0]))* 180/Math.PI));
			histogram.add(Math.atan(((val[3]-val[1])/(val[2]-val[0])) * 180/Math.PI)+90);
		}

		theta = Histogram.mean(histogram.getValues(histogram.getMax()));
		theta = 90 - theta;

		return theta;

	}
	
	
	/**
	 * Get the rotation of a scanned grid (assumes rotated about center).
	 * @param max_angle the maximum angle that could be considered
	 * @return the angle of rotation
	 */
	public double getRotation(double max_angle)
	{
		
		//load image as OpenCV Mat
		
		File fimg=null;
		try {
			fimg = File.createTempFile("imagedgrid", ".jpg");
//			System.out.println(fimg.getAbsolutePath());
			ImageUtility.save(fimg.getAbsolutePath(), image_rgb);
		} catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
		
		//load image as OpenCV Mat
		Mat img = Highgui.imread(fimg.getAbsolutePath());		
//		System.out.println("getRotation: Finished reading image");
		
		if(fimg.exists()){
			fimg.delete();
		}

		
		//threshold images to get only the ink
		Mat bw = new Mat();
		Imgproc.threshold(img, bw, 127, 255, Imgproc.ADAPTIVE_THRESH_GAUSSIAN_C);//(gray, bw, 0, 0, Imgproc.THRESH_OTSU);
//		System.out.println("getRotation: Finished thresholding image");
		
		//transform image in grayscale
		Mat bw_gray = new Mat();
		Imgproc.cvtColor(bw, bw_gray, Imgproc.COLOR_BGR2GRAY);
//		System.out.println("getRotation: Finished grayscaling image");
		
		//create edge map
		Mat edges = new Mat();
		int lowThreshold = 50;
		int ratio = 3;
		Imgproc.Canny(bw_gray, edges, lowThreshold, lowThreshold * ratio);
//		System.out.println("getRotation: Finished Cannying image");


		//compute hough lines
		Mat lines = new Mat();		
		int min_line_length=(int)Math.round(0.25*img.width())+1;
		int max_line_gap=(int)Math.round(0.025*img.width())+1;//min_line_length/10;//100
		int min_line_votes = (int)Math.round(0.1*img.width())+1;//1000;//1000
		double theta_resolution=1;

		Imgproc.HoughLinesP(edges, lines, 10, theta_resolution*Math.PI/180, min_line_votes, min_line_length, max_line_gap);
//		System.out.println("getRotation: angles acquired");


		//add lines to histogram
		Histogram<Double> histogram = new Histogram<Double>(Histogram.createDoubleBins(0, 1, 180));
		double theta;
		double ang;

		for(int i = 0; i < lines.cols(); i++) {
//			System.out.println("Col "+i+":");
			double[] val = lines.get(0, i);
			
//        	Core.line(img, new Point(val[0], val[1]), new Point(val[2], val[3]), new Scalar(0, 0, 255), 5);
			ang=Math.atan((val[3]-val[1])/(val[2]-val[0]))* 180/Math.PI;
//        	System.out.println("ANG = "+ang);
			histogram.add(ang+90);
		}
//		System.out.println("getRotation: angles added to histogram");

		
		
		int min_limit = (int)(90-max_angle);
		int max_limit = (int)(90+max_angle);
		double max=90; 
		double max_val=0;
		for(int i=min_limit; i<max_limit; i++){
//			System.out.println(i+" :"+histogram.get(i*1.0));
			if(histogram.get(i*1.0)>max_val){
				max=i;
				max_val=histogram.get(max);
			}
		}
//		System.out.println("getRotation: max angle computed");
		
		theta = Histogram.mean(histogram.getValues(max));
		theta = 90 - theta;

		return theta;
	}

	/**
	 * Rotate a scanned grid (assumes rotated about center).
	 * @param theta the angle of rotation
	 */
	public void rotate(double theta)
	{
		image_rgb = ImageUtility.rotate(image_rgb, theta, width/2, height/2);
		image_g = ImageUtility.rotate(image_g, width, height, theta, width/2, height/2);
	}

	/**
	 * Unrotate a scanned grid (assumes rotated about center).
	 * @param theta_max the maximum allowed rotation
	 * @return the angle of rotation
	 */
	public double unrotate(double theta_max)
	{
		double theta = getRotation(theta_max);
		
		if(Math.abs(theta) > theta_max) theta = 0;
		
		rotate(theta);
		
		if(SAVE_ROTATED_IMAGE){
			System.out.println("Rotation: " + theta);
			File fimg=null;
			try {
				fimg = File.createTempFile("imagedgrid-ROTATED", ".jpg");
				System.out.println("Rotated image saved to: "+fimg.getAbsolutePath());
				ImageUtility.save(fimg.getAbsolutePath(), image_rgb);
			} catch (IOException e) {
				// TODO Auto-generated catch block
				e.printStackTrace();
			}			
		}

		
		//ImageUtility.save("tmp/output_r.jpg", ImageUtility.to2D(ImageUtility.g2argb(image_g, width, height), width, height));
		return theta;
	}


	/**
     * Get edge sums.
     * @return the edge sums
     */
    public Pair<double[],double[]> getEdgeSums()
    {         
        double[] horizontal_sums = new double[width];
        double[] vertical_sums = new double[height];
        int at;
 
        double val;
        if(true){
//            double t0=System.currentTimeMillis();
            for(int x=0; x<width; x++){
                for(int y=0; y<height; y++){
                    val=-1;
                    for(int offsetx=-1;offsetx<=1;offsetx++){
                        if((x+offsetx)>=width||(x+offsetx)<0)
                            continue;
                        at = y*width+(x+offsetx);                 
//                        horizontal_sums[x] += image_g[at];
                        val=Math.max(val, image_g[at]);//keep the max value between the neighbors
                    }
                    horizontal_sums[x] +=val;//adds to line sum
                    val=-1;
                    for(int offsety=-1;offsety<=1;offsety++){
                        if((y+offsety)>=height||(y+offsety)<0)
                            continue;
                        at = (y+offsety)*width+x;                 
//                        vertical_sums[y] += image_g[at];
                        val=Math.max(val, image_g[at]);//keep the max value between the neighbors
                    }     
                    vertical_sums[y] +=val;//adds to col sum
                }
            }
            int off_x=(int)(width*0.01); //0.05 ideal but takes 3 times more time
            int off_y=(int)(height*0.01);
//            int min_y=(int)(height*0.18);
//            int max_y=(int)(height*0.82);
             
             
            ArrayList<Integer> indexes_x = new ArrayList<Integer>();
            double[]  values_x = new double[width];
            for(int i=0;i<width;i++)
                values_x[i]=horizontal_sums[i];
            //order the lines by the 'strongest' response
            for(int i=0; i<width;i++){//                if(y<min_y||y>max_y)
//                vertical_sums[y]=0;
                double max = -1;
                int max_index=-1;
                for(int j=0;j<width;j++){
                    if(values_x[j]>max){
                        max=values_x[j];
                        max_index=j;
                    }
                }
                if(max_index==-1)
                    break;
                indexes_x.add(max_index);
                for(int offset=-off_x; offset<=off_x; offset++){
                    if(max_index+offset>=width||max_index+offset<0)
                        continue;
                    if(offset!=0) horizontal_sums[max_index+offset]=0;
                    values_x[max_index+offset]=-1;
                }
            }
//            for(Integer x: indexes_x)
//                System.out.print(x+" ");
//            System.out.println();
 
 
            ArrayList<Integer> indexes_y = new ArrayList<Integer>();
            double[]  values_y = new double[height];
            for(int i=0;i<height;i++)
                values_y[i]=vertical_sums[i];
             
            //order the cols by the 'strongest' response
            for(int i=0; i<height;i++){
                double max = -1;
                int max_index=-1;
                for(int j=0;j<height;j++){
                    if(values_y[j]>max){
                        max=values_y[j];
                        max_index=j;
                    }
                }
                if(max_index==-1)
                    break;
                indexes_y.add(max_index);
                for(int offset=-off_y; offset<=off_y; offset++){
                    if(max_index+offset>=height||max_index+offset<0)
                        continue;
                    if(offset!=0) vertical_sums[max_index+offset]=0;
                    values_y[max_index+offset]=-1;
                }                 
            }
             
//            for(Integer y:indexes_y){
//                if(y<min_y||y>max_y)
//                    vertical_sums[y]=0;
//                System.out.print(y+" ");
//            }
//            System.out.println();
             
//            System.out.println("Elapsed time: " + ((System.currentTimeMillis()-t0)/1000.0) + " s");
        }
        else{
            for(int x=0; x<width; x++){
                for(int y=0; y<height; y++){
                    at = y*width+x;                 
                    horizontal_sums[x] += image_g[at];
                    vertical_sums[y] += image_g[at];
                }
            }
             
        }
        //Debug: save out edge sums
        if(false){             
            MatrixUtility.save("tmp/horizontal_sums.txt", horizontal_sums);
            MatrixUtility.save("tmp/vertical_sums.txt", vertical_sums);
        }
         
         
         
        return new Pair<double[],double[]>(horizontal_sums, vertical_sums);
    } 
	
	
	/**
	 * Filter the edge sums leaving only large values.
	 * @param sums the horizontal/vertical edge sums
	 * @return the filtered edge sums
	 */
	public Pair<double[],double[]> getFilteredEdgeSums(Pair<double[],double[]> sums)
	{
		Pair<double[],double[]> filtered_sums = new Pair<double[],double[]>();

		//Threshold sums based on image dimensions
		filtered_sums.first = MatrixUtility.subsasgn(sums.first, MatrixUtility.find(MatrixUtility.lt(sums.first, 0.2*height)), 0);
		filtered_sums.second = MatrixUtility.subsasgn(sums.second, MatrixUtility.find(MatrixUtility.lt(sums.second, 0.2*width)), 0);
		
		//Filter large sums that are next to other large sums
		for(int i=filtered_sums.first.length-1; i>=1; i--){
			if(filtered_sums.first[i]>0 && filtered_sums.first[i-1]>0){
				filtered_sums.first[i-1] = Math.max(filtered_sums.first[i], filtered_sums.first[i-1]);
				filtered_sums.first[i] = 0;
			}
		}	
		
		for(int i=filtered_sums.second.length-1; i>=1; i--){
			if(filtered_sums.second[i]>0 && filtered_sums.second[i-1]>0){
				filtered_sums.second[i-1] = Math.max(filtered_sums.second[i], filtered_sums.second[i-1]);
				filtered_sums.second[i] = 0;
			}
		}
		
		//Binarize
		if(false){
			filtered_sums.first = MatrixUtility.gt(filtered_sums.first, 0.5);
			filtered_sums.second = MatrixUtility.gt(filtered_sums.second, 0.5);
		}
		
		//Debug: save filtered edge sums
		if(false){			
			MatrixUtility.save("tmp/filtered_horizontal_sums.txt", filtered_sums.first);
			MatrixUtility.save("tmp/filtered_vertical_sums.txt", filtered_sums.second);
		}
		
		return filtered_sums;
	}
	
	/**
	 * Filter the edge sums with only large values intact.
	 * @return the filtered edge sums
	 */
	public Pair<double[],double[]> getFilteredEdgeSums()
	{
		return getFilteredEdgeSums(getEdgeSums());
	}
	
	/**
	 * Get the baseline of an image containing text (i.e. the center line of the text)
	 * @return the baseline
	 */
	public int getBaseline_Max()
	{
		Pair<double[],double[]> edge_sums = getEdgeSums();
		return MatrixUtility.max_index(edge_sums.second);
	}
	
	/**
	 * Get the baseline of an image containing text (i.e. the center line of the text)
	 * @return the baseline
	 */
	public int getBaseline_Mean()
	{
		Pair<double[],double[]> edge_sums = getEdgeSums();
		double sum = 0;
		int count = 0;
		
		for(int y=0; y<height; y++){
			sum += y * edge_sums.second[y];
			count += edge_sums.second[y];
		}
		
		return (int)Math.round(sum/count);
	}
	
	
	/**
	 * Label horizontal/vertical lines in the image.
	 * @return the indices of horizontal/vertical lines
	 */
	public Pair<Vector<Integer>,Vector<Integer>> labelGridLines()
	{
		Vector<Integer> horizontal_lines = new Vector<Integer>();
		Vector<Integer> vertical_lines = new Vector<Integer>();
		
		int viewer_width = 1200;
		ImageViewer viewer = new ImageViewer(image_rgb, width, height, viewer_width);
		Triple<Integer,Integer,Integer> click;
		int[][] displayed_image;
		Integer scroll_direction;
		
		//displayed_image = ImageUtility.copy(image_rgb);
		viewer.enableEventBuffer(true);
		
		while(viewer.isVisible()){
			click = viewer.getBufferedClickTriple();
			
			if(click != null){
				if(click.third == 1){
					horizontal_lines.add((int)Math.round(click.second * width/viewer_width));
				}else if(click.third == 3){
					vertical_lines.add((int)Math.round(click.first * width/viewer_width));
				}
			}
			
			scroll_direction = viewer.getBufferedWheelEvent();
			
			if(scroll_direction != null){
				if(scroll_direction < 0){
					if(!vertical_lines.isEmpty()){
						vertical_lines.removeElementAt(vertical_lines.size()-1);
					}
				}else{
					if(!horizontal_lines.isEmpty()){
						horizontal_lines.removeElementAt(horizontal_lines.size()-1);
					}
				}
			}
			
			if(click != null || scroll_direction != null){
				displayed_image = ImageUtility.copy(image_rgb);
				drawLines(displayed_image, horizontal_lines, vertical_lines, 0x00ff0000, 5);
				viewer.set(displayed_image, width, height);
			}
		}
		
		Collections.sort(horizontal_lines);
		Collections.sort(vertical_lines);
				
		return new Pair<Vector<Integer>,Vector<Integer>>(horizontal_lines, vertical_lines);
	}

	/**
	 * Filter so as to preserve horizontal and vertical lines.
	 * @param threshold threshold to determine line responses
	 * @param weight weight for positive line responses
	 */
	public void filterHVLines(double threshold, double weight)
	{
		double[][] fh = new double[9][9];
		double[][] fv = new double[9][9];
		double[] ih, iv;
		int at;
		
		//Construct filters
		for(int i=0; i<9; i++){
			fh[i][4] = 1.0/9.0;
			fv[4][i] = 1.0/9.0;
		}
		
		ih = ImageUtility.convolve(image_g, width, height, fh);
		iv = ImageUtility.convolve(image_g, width, height, fv);
		
		//Combine and threshold responses
		for(int x=0; x<width; x++){
			for(int y=0; y<height; y++){
				at = y*width + x;
				image_g[at] = (ih[at]+iv[at]) / 2.0;
				
				if(image_g[at] > threshold){
					image_g[at] = weight;
				}else{
					image_g[at] = 0;
				}
			}
		}
	}

	/**
	 * Get horizontal/vertical lines from the image.
	 * @param filtered_sums the filtered horizontal/vertical edge sums
	 * @return the indices of horizontal/vertical lines
	 */
	public Pair<Vector<Integer>,Vector<Integer>> getGridLines(Pair<double[],double[]> filtered_sums)
	{
		Vector<Integer> horizontal_lines = new Vector<Integer>();
		Vector<Integer> vertical_lines = new Vector<Integer>();
		
		//Extract indices of large sums
		for(int i=0; i<filtered_sums.first.length; i++){
			if(filtered_sums.first[i] > 0){
				vertical_lines.add(i);
			}
		}
		
		for(int i=0; i<filtered_sums.second.length; i++){
			if(filtered_sums.second[i] > 0){
				horizontal_lines.add(i);
			}
		}
		
		return new Pair<Vector<Integer>,Vector<Integer>>(horizontal_lines, vertical_lines);
	}
	
	/**
	 * Get horizontal/vertical lines from the image.
	 * @return the indices of horizontal/vertical lines
	 */
	public Pair<Vector<Integer>,Vector<Integer>> getGridLines()
	{
		return getGridLines(getFilteredEdgeSums());
	}

	
	

	/**
   * Convert a 1D image into a 2D image.
   *  @param img1D the 1D version of the image
   *  @param w the width of the image
   *  @param h the height of the image
   *  @return the 2D version of the image
   */
  public static double[][] to2D(double[] img1D, int w, int h)
  {
  	double[][] img2D = new double[h][w];
  	
  	for(int x=0; x<w; x++){
  		for(int y=0; y<h; y++){
  			img2D[y][x] = img1D[y*w+x];
  		}
  	}
  	
  	return img2D;
  }
	
	
  /**
	 * Get horizontal/vertical lines from the image by matching found lines with a template.
	 * @param template_lines the template lines
	 * @param FORCE_EDGE_RESPONSES true of alignment should always use edge responses to determine a match
	 * @return the indices of horizontal/vertical lines
	 */
	public Pair<Vector<Integer>,Vector<Integer>> getGridLines(Pair<Vector<Integer>,Vector<Integer>> template_lines, boolean FORCE_EDGE_RESPONSES)
	{
		return getGridLines(template_lines, FORCE_EDGE_RESPONSES, false, "");
	}
	
	/**
	 * Get horizontal/vertical lines from the image by matching found lines with a template.
	 * @param template_lines the template lines
	 * @param FORCE_EDGE_RESPONSES true of alignment should always use edge responses to determine a match
	 * @param resize_template whether to resize the template before matching the lines
	 * @param state the state name  abbreviation
	 * @return the indices of horizontal/vertical lines
	 */
	public Pair<Vector<Integer>,Vector<Integer>> getGridLines(Pair<Vector<Integer>,Vector<Integer>> template_lines_const, boolean FORCE_EDGE_RESPONSES, boolean resize_template, String state)
	{	
		Pair<Vector<Integer>,Vector<Integer>> template_lines = new Pair<Vector<Integer>,Vector<Integer>>();
		template_lines.first= new Vector<Integer>();
		for(Integer i:template_lines_const.first)
			template_lines.first.add(new Integer(i));
		template_lines.second= new Vector<Integer>();
		for(Integer i:template_lines_const.second)
			template_lines.second.add(new Integer(i));

//		FORCE_EDGE_RESPONSES=true;
		Pair<double[],double[]> filtered_edge_sums = getFilteredEdgeSums();
		Pair<double[],double[]> smoothed_filtered_edge_sums = new Pair<double[],double[]>();
		Pair<Vector<Integer>,Vector<Integer>> image_lines = getGridLines(filtered_edge_sums);
		Pair<Vector<Integer>,Vector<Integer>> mapped_lines = new Pair<Vector<Integer>,Vector<Integer>>();
		double horizontal_flexibility=0.1, vertical_flexibility=0.2;
		smoothed_filtered_edge_sums = smoothEdgeSums(filtered_edge_sums);
		
		if(resize_template){
			//rescaling template
			double template_image_height=height, template_image_width=width;
			if(state.equalsIgnoreCase("1930_AK")){
				template_image_height=3656;
				template_image_width=6192;
				horizontal_flexibility=0.025;
				vertical_flexibility=0.025;
			}
			else if(state.equalsIgnoreCase("1930_AS")){
				template_image_height=926;
				template_image_width=1104;
				horizontal_flexibility=0.025;
				vertical_flexibility=0.025;
			}
			else if(state.equalsIgnoreCase("1930_HI")){
				template_image_height=1342;
				template_image_width=1936;
				horizontal_flexibility=0.1;
				vertical_flexibility=0.2;
			}
			if(state.equalsIgnoreCase("1930_NC")){
				template_image_height=3712;
				template_image_width=5388;
				horizontal_flexibility=0.025;
				vertical_flexibility=0.2;//0.025;
			}
			else if (state.equalsIgnoreCase("1930_WA")){
				template_image_height=5360;
				template_image_width=7824;
				horizontal_flexibility=0.025;
				vertical_flexibility=0.025;
			}
			else if(state.startsWith("1930_")){
				template_image_height=5544;
				template_image_width=7872;
				horizontal_flexibility=0.025;
				vertical_flexibility=0.2;
			}
			else if(state.equalsIgnoreCase("AK_1940")){
                template_image_height=4592;
                template_image_width=7620;
                horizontal_flexibility=0.025;
                vertical_flexibility=0.2;
            }
			else if(state.equalsIgnoreCase("AS_1940")){//empty ones missing one column
                template_image_height=3584;
                template_image_width=4500;
                horizontal_flexibility=0.025;
                vertical_flexibility=0.2;
            }
			else if (state.endsWith("_1940")){
                template_image_height=2643;
                template_image_width=3400;
                horizontal_flexibility=0.1; //0.1: AL, AR, AZ, CA, CO, CT (1 bad), 
                							//DC, DE, FL (2 1st line), GA, IA, ID, IL, IN, KS, KY, LA, MA
                							//MD (1 1st line), ME, MI, MN (1 1st line), MO, MS (6 1st line, 2 rotation)
                							//MT, NC, ND, NE, NH, NJ (2 bad), NM (1 1st line), NV (1 1st line)
                							//NY, OH, OK (4 bad, 1 1st line)
                vertical_flexibility=0.2;				
			}
			else {
				System.out.println("Unrecognized state requested: " + state);
			}
			for(int i=0; i<template_lines.first.size();i++){
				template_lines.first.set(i, (int)Math.round(template_lines.first.get(i)*(height/template_image_height)));
			}
			for(int i=0; i<template_lines.second.size();i++){
				template_lines.second.set(i, (int)Math.round(template_lines.second.get(i)*(width/template_image_width)));
			}
//			for(int i=0; i<template_lines.first.size();i++){
//				System.out.print(template_lines.first.get(i)+" ");
//			}
//			System.out.println();
//			for(int i=0; i<template_lines.second.size();i++){
//				System.out.print(template_lines.second.get(i)+" ");
//			}
//			System.out.println();
//			
		}
		
		
		if(getPeriod(template_lines.first, 4) >= 0 || FORCE_EDGE_RESPONSES){
//			System.out.print("Horizontal line match (periodic): ");
			mapped_lines.first = matchLines(template_lines.first, image_lines.first, (int)Math.round(horizontal_flexibility*height), 0.8, 1.2, smoothed_filtered_edge_sums.second);
		}else{
//			System.out.print("Horizontal line match (non-periodic): ");
			mapped_lines.first = matchLines(template_lines.first, image_lines.first, (int)Math.round(horizontal_flexibility*height), 0.8, 1.2);
		}
			
		
		if(getPeriod(template_lines.second, 4) >= 0 || FORCE_EDGE_RESPONSES){
//			System.out.print("Vertical line match (periodic): ");
			mapped_lines.second = matchLines(template_lines.second, image_lines.second, (int)Math.round(vertical_flexibility*width), 0.8, 1.2, smoothed_filtered_edge_sums.first);
		}else{
//			System.out.print("Vertical line match (non-periodic): ");
			mapped_lines.second = matchLines(template_lines.second, image_lines.second, (int)Math.round(vertical_flexibility*width), 0.8, 1.2);
		}
		
		if(SHOW_TEMPLATE_ALIGNMENT && image_rgb[0].length>1000){
			int[][] displayed_image = ImageUtility.copy(image_rgb);
//			int[][] test = ImageUtility.copy(image_rgb);
//			int[][] test2 = ImageUtility.copy(image_rgb);
//			int[][] test3 = ImageUtility.g2argb(to2D(image_g, width, height));
//			ImageViewer.show(test3, width, height, 1200, "Lines");
//			drawLines(test, template_lines, 0x000000ff, 3);
//			drawLines(test, mapped_lines, 0x0000ff00, 3);
//			drawLines(test, image_lines, 0x00ff0000, 3);
//			ImageViewer.show(test, width, height, 1200, "Lines");
			//System.out.println(image_lines.first.get(1));
			//System.out.println(image_lines.second.get(1));
//			drawLines(displayed_image, image_lines, 0x00ff0000, 3);
			//blue for template placement
//			drawLines(test, template_lines, 0x000000ff, 3);
//			ImageViewer.show(test, width, height, 1200, "Template Lines");
			//red for image lines
//			drawLines(test2, image_lines, 0x00ff0000, 3);
//			ImageViewer.show(test2, width, height, 1200, "Image Lines");
			//green for mapped lines
			drawLines(displayed_image, mapped_lines, 0x0000ff00, 3);
			ImageViewer.show(displayed_image, width, height, 1200, "Mapped Lines");
		}
		
		return mapped_lines;
	}
	
	/**
	 * Get horizontal/vertical lines from the image by matching found lines with a template.
	 * @param filename the filename of the template
	 * @return the indices of horizontal/vertical lines
	 */
	public Pair<Vector<Integer>,Vector<Integer>> getGridLines(String filename, boolean resize_template, String state)
	{		
		return getGridLines(loadLines(filename), true, resize_template, state);
	}
	
	/**
	 * Get the sub-image at the given location.
	 * @param theta the rotation to apply to the original image before extracting the sub-image
	 * @param x the x-coordinate of the upper left corner of the desired sub-image
	 * @param y the y-coordinate of the upper left corner of the desired sub-image
	 * @param w the width of the sub-image
	 * @param h the height of the sub-image
	 * @return the sub-image
	 */
	public int[][] getSubimage(double theta, int x0, int y0, int w, int h)
	{
		int[][] subimage = new int[h][w];
		double c = Math.cos(-theta*Math.PI/180);
		double s = Math.sin(-theta*Math.PI/180);
		int xc = width / 2;
		int yc = height / 2;  	
		int xi, yi;
	
		for(int x=0; x<w; x++){
			for(int y=0; y<h; y++){
				xi = (int)Math.round((x+x0-xc)*c - (y+y0-yc)*s + xc);
				yi = (int)Math.round((x+x0-xc)*s + (y+y0-yc)*c + yc);
				
				if(xi>=0 && xi<width && yi>=0 && yi<height){
					subimage[y][x] = image_rgb[yi][xi];
				}
			}
		}
		
		return subimage;
	}
	
	/**
	 * Get the sub-image of the cell at the given row/column using the provided grid lines.
	 * @param theta the rotation to apply to the original image before extracting the sub-image
	 * @param lines the grid lines to use
	 * @param row the row
	 * @param column the column
	 * @return the cell image
	 */
	public int[][] getCell(double theta, Pair<Vector<Integer>,Vector<Integer>> lines, int row, int column)
	{
		int x0 = lines.second.get(column);
		int y0 = lines.first.get(row);
		int x1 = lines.second.get(column+1);
		int y1 = lines.first.get(row+1);
				
		return getSubimage(theta, x0, y0, x1-x0+1, y1-y0+1);
	}
	
	/**
	 * Get the sub-image of the cell at the given row/column using the provided grid lines padding as much as possible considering neighboring cells.
	 * @param theta the rotation to apply to the original image before extracting the sub-image
	 * @param lines the grid lines to use
	 * @param row the row
	 * @param column the column
	 * @return the cell image
	 */
	public int[][] getPaddedCell(double theta, Pair<Vector<Integer>,Vector<Integer>> lines, int row, int column)
	{
		int x0 = lines.second.get(column);
		int y0 = lines.first.get(row);
		int x1 = lines.second.get(column+1);
		int y1 = lines.first.get(row+1);
		int w = x1 - x0;
		int h = y1 - y0;
		
		if(column > 0){
			x0 -= (x0-lines.second.get(column-1)) / 2.0;
		}else{
			x0 -= w / 2;
		}
		
		if(row > 0){
			y0 -= (y0-lines.first.get(row-1)) / 2.0;
		}else{
			y0 -= h / 2;
		}
		
		if(column < lines.second.size()-2){
			x1 += (lines.second.get(column+2)-x1) / 2.0;
		}else{
			x1 += w / 2;
		}
		
		if(row < lines.first.size()-2){
			y1 += (lines.first.get(row+2)-y1) / 2.0;
		}else{
			y1 += h / 2;
		}
		
		return getSubimage(theta, x0, y0, x1-x0+1, y1-y0+1);
	}
	
	/**
	 * Get the sub-image of the cell at the given row/column using the provided grid lines padding each side.
	 * @param theta the rotation to apply to the original image before extracting the sub-image
	 * @param lines the grid lines to use
	 * @param row the row
	 * @param column the column
	 * @param padding the percentage to pad along each dimension
	 * @return the cell image
	 */
	public int[][] getPaddedCell(double theta, Pair<Vector<Integer>,Vector<Integer>> lines, int row, int column, double padding)
	{
		int x0 = lines.second.get(column);
		int y0 = lines.first.get(row);
		int x1 = lines.second.get(column+1);
		int y1 = lines.first.get(row+1);
		int w = x1 - x0 + 1;
		int h = y1 - y0 + 1;
		
		x0 -= padding * w;
		x1 += padding * w;
		y0 -= padding * h;
		y1 += padding * h;
		
		return getSubimage(theta, x0, y0, x1-x0+1, y1-y0+1);
	}
	
	/**
	 * Get the sub-image of the cell at the given row/column using the provided grid lines refining it to best fit the surrounding lines.
	 * @param theta1 the rotation to apply to the original image before extracting the sub-image
	 * @param lines the grid lines to use
	 * @param row the row
	 * @param column the column
	 * @param theta_max the maximum allowed rotation refinement
	 * @param offset_max the maximum percentage of allowed offset refinement
	 * @return the cell image
	 */
	public int[][] getRefinedCell(double theta1, Pair<Vector<Integer>,Vector<Integer>> lines, int row, int column, double theta_max, double offset_max)
	{
		double padding = 0.15;
		ImagedGrid padded_cell = new ImagedGrid(getPaddedCell(theta1, lines, row, column, padding));
		int[][] cell = getCell(theta1, lines, row, column);
		int cell_width = cell[0].length;
		int cell_height = cell.length;
		Pair<double[],double[]> edge_sums;
		int minx = (int)Math.round(padding * cell_width);
		int miny = (int)Math.round(padding * cell_height);
		int maxx = padded_cell.getWidth() - minx;
		int maxy = padded_cell.getHeight() - miny;
		int maxi = 0;
		double maxv;
		double theta2;

		//cell.thin();
		padded_cell.hilditch();
		theta2 = padded_cell.getRotation();
		if(Math.abs(theta2) <= theta_max) padded_cell.rotate(theta2);
		//cell.show();
		
		edge_sums = padded_cell.getEdgeSums();
		edge_sums = smoothEdgeSums(edge_sums);	//Crucial as horiz/vert lines may not be perfectly aligned still!
		
		//Find best left line
		maxv = -Double.MAX_VALUE;
		
		for(int i=0; i<edge_sums.first.length/2; i++){
			if(edge_sums.first[i] > maxv){
				maxv = edge_sums.first[i];
				maxi = i;
			}
		}
		
		if(Math.abs(maxi-minx) <= offset_max*cell_width) minx = maxi;
		
		//Find best right line
		maxv = -Double.MAX_VALUE;
		
		for(int i=edge_sums.first.length/2; i<edge_sums.first.length; i++){
			if(edge_sums.first[i] > maxv){
				maxv = edge_sums.first[i];
				maxi = i;
			}
		}
		
		if(Math.abs(maxi-maxx) <= offset_max*cell_width) maxx = maxi;
		
		//Find best top line
		maxv = -Double.MAX_VALUE;
		
		for(int i=0; i<edge_sums.second.length/2; i++){
			if(edge_sums.second[i] > maxv){
				maxv = edge_sums.second[i];
				maxi = i;
			}
		}
		
		if(Math.abs(maxi-miny) <= offset_max*cell_height) miny = maxi;
		
		//Find best bottom line
		maxv = -Double.MAX_VALUE;
		
		for(int i=edge_sums.second.length/2; i<edge_sums.second.length; i++){
			if(edge_sums.second[i] > maxv){
				maxv = edge_sums.second[i];
				maxi = i;
			}
		}
		
		if(Math.abs(maxi-maxy) <= offset_max*cell_height) maxy = maxi;
			
		return ImageUtility.crop(padded_cell.getColorImage(), minx, miny, maxx, maxy);
	}

	/**
	 * Get the sub-image of the cell at the given row/column using the provided grid lines refining it to best fit the surrounding lines.
	 * @param theta the rotation to apply to the original image before extracting the sub-image
	 * @param lines the grid lines to use
	 * @param row the row
	 * @param column the column
	 * @return the cell image
	 */
	public int[][] getRefinedCell(double theta, Pair<Vector<Integer>,Vector<Integer>> lines, int row, int column)
	{
		return getRefinedCell(theta, lines, row, column, 4, 0.2);
	}
	
	/**
	 * Get the location of the cell at the given row/column using the provided grid lines refining it to best fit the surrounding lines.
	 * @param theta1 the rotation to apply to the original image before extracting the sub-image
	 * @param lines the grid lines to use
	 * @param row the row
	 * @param column the column
	 * @param theta_max the maximum allowed rotation refinement
	 * @param offset_max the maximum percentage of allowed offset refinement
	 * @return the cell location
	 */
	public CellLocation getRefinedCellLocation(double theta1, Pair<Vector<Integer>,Vector<Integer>> lines, int row, int column, double theta_max, double offset_max)
	{
		double padding = 0.15;
		ImagedGrid padded_cell = new ImagedGrid(getPaddedCell(theta1, lines, row, column, padding));
		Pair<double[],double[]> edge_sums;
		double theta2;
		
		int x0 = lines.second.get(column);
		int y0 = lines.first.get(row);
		int x1 = lines.second.get(column+1);
		int y1 = lines.first.get(row+1);
		int cell_width = x1 - x0 + 1;
		int cell_height = y1 - y0 + 1;
		int cell_padding_x = (int)Math.round(padding * cell_width);
		int cell_padding_y = (int)Math.round(padding * cell_height);
		int minx = cell_padding_x;
		int miny = cell_padding_y;
		int maxx = padded_cell.getWidth() - cell_padding_x;
		int maxy = padded_cell.getHeight() - cell_padding_y;
		int maxi = 0;
		double maxv;
		double sx, sy, tx, ty;
		double[][] M;

		//cell.thin();
		padded_cell.hilditch();
		theta2 = padded_cell.getRotation();
		if(Math.abs(theta2) <= theta_max) padded_cell.rotate(theta2);
		//cell.show();
		
		edge_sums = padded_cell.getEdgeSums();
		edge_sums = smoothEdgeSums(edge_sums);	//Crucial as horiz/vert lines may not be perfectly aligned still!
		
		//Find best left line
		maxv = -Double.MAX_VALUE;
		
		for(int i=0; i<edge_sums.first.length/2; i++){
			if(edge_sums.first[i] > maxv){
				maxv = edge_sums.first[i];
				maxi = i;
			}
		}
		
		if(Math.abs(maxi-minx) <= offset_max*cell_width) minx = maxi;
		
		//Find best right line
		maxv = -Double.MAX_VALUE;
		
		for(int i=edge_sums.first.length/2; i<edge_sums.first.length; i++){
			if(edge_sums.first[i] > maxv){
				maxv = edge_sums.first[i];
				maxi = i;
			}
		}
		
		if(Math.abs(maxi-maxx) <= offset_max*cell_width) maxx = maxi;
		
		//Find best top line
		maxv = -Double.MAX_VALUE;
		
		for(int i=0; i<edge_sums.second.length/2; i++){
			if(edge_sums.second[i] > maxv){
				maxv = edge_sums.second[i];
				maxi = i;
			}
		}
		
		if(Math.abs(maxi-miny) <= offset_max*cell_height) miny = maxi;
		
		//Find best bottom line
		maxv = -Double.MAX_VALUE;
		
		for(int i=edge_sums.second.length/2; i<edge_sums.second.length; i++){
			if(edge_sums.second[i] > maxv){
				maxv = edge_sums.second[i];
				maxi = i;
			}
		}
		
		if(Math.abs(maxi-maxy) <= offset_max*cell_height) maxy = maxi;
			
		//Construct transformation
		sx = maxx - minx + 1;
		sy = maxy - miny + 1;
		tx = x0 + sx/2 + minx - cell_padding_x;
		ty = y0 + sy/2 + miny - cell_padding_y;
		
		M = MatrixUtility.scale(sx, sy);
		if(Math.abs(theta2) <= theta_max) M = MatrixUtility.mtimes(MatrixUtility.rotate(theta2), M);
		M = MatrixUtility.mtimes(MatrixUtility.translate(tx, ty), M);
		M = MatrixUtility.mtimes(MatrixUtility.translate(-width/2, -height/2), M);
		M = MatrixUtility.mtimes(MatrixUtility.rotate(-theta1), M);
		M = MatrixUtility.mtimes(MatrixUtility.translate(width/2, height/2), M);
		
		return new CellLocation(M);
	}
	
	
	/**
	 * Get the location of the cell at the given row/column using the provided grid lines refining it to best fit the surrounding lines.
	 * @param theta1 the rotation to apply to the original image before extracting the sub-image
	 * @param lines the grid lines to use
	 * @param row the row
	 * @param column the column
	 * @param theta_max the maximum allowed rotation refinement
	 * @param offset_max the maximum percentage of allowed offset refinement
	 * @param thresh the threshold to be used in the binarization process
	 * @return the cell location
	 */
	public CellLocation getRefinedCellLocation(double theta1, Pair<Vector<Integer>,Vector<Integer>> lines, int row, int column, double theta_max, double offset_max, double thresh)
	{
		double padding = 0.15;
		ImagedGrid padded_cell = new ImagedGrid(getPaddedCell(theta1, lines, row, column, padding), thresh);
		Pair<double[],double[]> edge_sums;
		double theta2;
		
		int x0 = lines.second.get(column);
		int y0 = lines.first.get(row);
		int x1 = lines.second.get(column+1);
		int y1 = lines.first.get(row+1);
		int cell_width = x1 - x0 + 1;
		int cell_height = y1 - y0 + 1;
		int cell_padding_x = (int)Math.round(padding * cell_width);
		int cell_padding_y = (int)Math.round(padding * cell_height);
		int minx = cell_padding_x;
		int miny = cell_padding_y;
		int maxx = padded_cell.getWidth() - cell_padding_x;
		int maxy = padded_cell.getHeight() - cell_padding_y;
		int maxi = 0;
		double maxv;
		double sx, sy, tx, ty;
		double[][] M;

		//cell.thin();
		padded_cell.hilditch();
		theta2 = padded_cell.getRotation();
		if(Math.abs(theta2) <= theta_max) padded_cell.rotate(theta2);
		//cell.show();
		
		edge_sums = padded_cell.getEdgeSums();
		edge_sums = smoothEdgeSums(edge_sums);	//Crucial as horiz/vert lines may not be perfectly aligned still!
		
		//Find best left line
		maxv = -Double.MAX_VALUE;
		
		for(int i=0; i<edge_sums.first.length/2; i++){
			if(edge_sums.first[i] > maxv){
				maxv = edge_sums.first[i];
				maxi = i;
			}
		}
		
		if(Math.abs(maxi-minx) <= offset_max*cell_width) minx = maxi;
		
		//Find best right line
		maxv = -Double.MAX_VALUE;
		
		for(int i=edge_sums.first.length/2; i<edge_sums.first.length; i++){
			if(edge_sums.first[i] > maxv){
				maxv = edge_sums.first[i];
				maxi = i;
			}
		}
		
		if(Math.abs(maxi-maxx) <= offset_max*cell_width) maxx = maxi;
		
		//Find best top line
		maxv = -Double.MAX_VALUE;
		
		for(int i=0; i<edge_sums.second.length/2; i++){
			if(edge_sums.second[i] > maxv){
				maxv = edge_sums.second[i];
				maxi = i;
			}
		}
		
		if(Math.abs(maxi-miny) <= offset_max*cell_height) miny = maxi;
		
		//Find best bottom line
		maxv = -Double.MAX_VALUE;
		
		for(int i=edge_sums.second.length/2; i<edge_sums.second.length; i++){
			if(edge_sums.second[i] > maxv){
				maxv = edge_sums.second[i];
				maxi = i;
			}
		}
		
		if(Math.abs(maxi-maxy) <= offset_max*cell_height) maxy = maxi;
			
		//Construct transformation
		sx = maxx - minx + 1;
		sy = maxy - miny + 1;
		tx = x0 + sx/2 + minx - cell_padding_x;
		ty = y0 + sy/2 + miny - cell_padding_y;
		
		M = MatrixUtility.scale(sx, sy);
		if(Math.abs(theta2) <= theta_max) M = MatrixUtility.mtimes(MatrixUtility.rotate(theta2), M);
		M = MatrixUtility.mtimes(MatrixUtility.translate(tx, ty), M);
		M = MatrixUtility.mtimes(MatrixUtility.translate(-width/2, -height/2), M);
		M = MatrixUtility.mtimes(MatrixUtility.rotate(-theta1), M);
		M = MatrixUtility.mtimes(MatrixUtility.translate(width/2, height/2), M);
		
		return new CellLocation(M);
	}
	
	
	/**
	 * Load an image using im2learn.
	 * @param filename the filename of the image to load
	 * @return the image
	 */
	public static int[][] load(String filename)//XXXX
	{
		int[][] image = null;
		
		try{
			Logger.getRootLogger().setLevel(Level.OFF);
			ImageObject image_object = ImageLoader.readImage(filename);
			byte[] bytes = (byte[])image_object.getData();
			int w, h, value;
			
			w = image_object.getNumCols();
			h = image_object.getNumRows();
			image = new int[h][w];
	
			for(int x=0; x<w; x++){
				for(int y=0; y<h; y++){
					value = bytes[y*w + x] & 0xff;
					image[y][x] = (value << 16) | (value << 8) | value;
				}
			}
		}catch(Exception e) {e.printStackTrace();}
		
		return image;
	}

	/**
	 * Thin the given image.  
	 * Note: this version ignores the opposite end of the structuring elements, sacrificing connectivity while gaining a speedup.
	 * @param Ig a grayscale image
	 * @param w the width of the image
	 * @param h the height of the image
	 */
	public static void thin(double[] Ig, int w, int h)
	{		
		int c, t, b, l, r, tl, tr, bl, br;
		boolean THINNING = true;
		
		while(THINNING){
			THINNING = false;
			
			for(int x=1; x<w-1; x++){
				for(int y=1; y<h-1; y++){
					c = y*w+x;
					
					if(Ig[c] > 0){
						l = c-1;
						r = c+1;
						
						t = (y-1)*w+x;
						tl = t-1;
						tr = t+1;
						
						b = (y+1)*w+x;
						bl = b-1;
						br = b+1;
						
						if((Ig[tl]>0 && Ig[t]>0 && Ig[tr]>0) ||	//Top
							 (Ig[t]>0 && Ig[tr]>0 && Ig[r]>0) ||	//Top right
							 (Ig[tr]>0 && Ig[r]>0 && Ig[br]>0) ||	//Right
							 (Ig[r]>0 && Ig[br]>0 && Ig[b]>0) ||	//Bottom right
							 (Ig[br]>0 && Ig[b]>0 && Ig[bl]>0) ||	//Bottom
							 (Ig[b]>0 && Ig[bl]>0 && Ig[l]>0) ||	//Bottom left
							 (Ig[bl]>0 && Ig[l]>0 && Ig[tl]>0) ||	//Left
							 (Ig[l]>0 && Ig[tl]>0 && Ig[t]>0)){		//Top Left
							Ig[c] = 0;
							THINNING = true;
						}
					}
				}
			}
		}
	}
	
	/**
	 * Remove borders.
	 * Note: always removes a little!
	 */
	public void removeBorders()
	{
		Pair<double[],double[]> edge_sums = getEdgeSums();
		double horizontal_threshold = 0.8 * width;
		double vertical_threshold = 0.8 * height;
		
		//Top
		for(int y=0; y<height; y++){
			for(int x=0; x<width; x++) image_g[y*width+x] = 0;
			if(edge_sums.second[y] < horizontal_threshold) break;
		}
		
		//Bottom
		for(int y=height-1; y>=0; y--){
			for(int x=0; x<width; x++) image_g[y*width+x] = 0;
			if(edge_sums.second[y] < horizontal_threshold) break;
		}
		
		//Left
		for(int x=0; x<width; x++){
			for(int y=0; y<height; y++) image_g[y*width+x] = 0;
			if(edge_sums.first[x] < vertical_threshold) break;
		}
		
		//Left
		for(int x=width-1; x>=0; x--){
			for(int y=0; y<height; y++) image_g[y*width+x] = 0;
			if(edge_sums.first[x] < vertical_threshold) break;
		}
	}
	
	/**
	 * Remove noise (i.e. small isolated points)
	 * @param r neighborhood radius
	 * @param p the percentage of pixels required to keep the point at the center of the neighborhood
	 */
	public void removeNoise(int r, double p)
	{
		double[] image_g_new = new double[width*height];
		int threshold = (int)Math.round(p * (2*r+1)*(2*r+1));
		int minx, maxx, miny, maxy;
		int count;
		
		for(int x=0; x<width; x++){
			for(int y=0; y<height; y++){
				minx = x - r;
				maxx = x + r;
				miny = y - r;
				maxy = y + r;
				
				if(minx < 0) minx = 0;
				if(maxx >= width) maxx = width - 1;
				if(miny < 0) miny = 0;
				if(maxy >= height) maxy = height - 1;
				
				count = 0;
				
				for(int u=minx; u<=maxx; u++){
					for(int v=miny; v<=maxy; v++){
						if(image_g[v*width+u] > 0.5) count++;
					}
				}
				
				if(count >= threshold){
					image_g_new[y*width+x] = image_g[y*width+x];
				}
			}
		}
		
		image_g = image_g_new;
	}
	
	/**
	 * Post process a cells contents.
	 * @param cell the cell image
	 * @return the process cell image
	 */
	public static double[] postProcess(int[][] cell)
	{
		int h = cell.length;
		int w = cell[0].length;
		double[] cell_g = ImageUtility.g2bw(ImageUtility.argb2g(cell), w, h, 0.75);
		
		cell_g = ImageUtility.getNegative(cell_g);
		ImageUtility.hilditch(cell_g, w, h);
		
		return cell_g;
	}

	/**
	 * Convert a vector of integers into an array of doubles.
	 * @param v a vector of integers
	 * @return an array of doubles
	 */
	public static double[] vector(Vector<Integer> v)
	{
		double[] a = new double[v.size()];
		
		for(int i=0; i<v.size(); i++){
			a[i] = v.get(i);
		}
		
		return a;
	}

	/**
	 * Get the period of the given horizontal/vertical lines.
	 * @param lines horizontal or vertical line positions (must be sorted!)
	 * @param threshold the threshold for determining periodicity
	 * @return the period (-1 if not periodic)
	 */
	public static double getPeriod(Vector<Integer> lines, double threshold)
	{		
		double[] diff = MatrixUtility.abs(MatrixUtility.diff(vector(lines)));
		double mean = MatrixUtility.mean(diff);
		double std = MatrixUtility.std(diff, mean);
				
		if(std <= threshold){
			return mean;
		}else{
			return -1;
		}
	}

	/**
	 * Get the period of the given noisy horizontal/vertical lines.
	 * @param lines noisy horizontal or vertical line positions (must be sorted!)
	 * @return the period
	 */
	public static double getNoisyPeriod(Vector<Integer> lines)
	{		
		double[] diff = MatrixUtility.abs(MatrixUtility.diff(vector(lines)));
		Histogram<Integer> histogram = new Histogram<Integer>(Histogram.createIntegerBins(0, 1, 200));
		
		for(int i=0; i<diff.length; i++){
			histogram.add((int)diff[i]);
		}
		
		return Histogram.mean(histogram.getValues(histogram.getMax()));
	}

	/**
	 * Smooth the given edge sums.
	 * @param edge_sums the edge sums
	 * @param filter_width the width of the smoothing filter
	 * @param filter_sigma the standard deviation of the smoothing filter
	 * @return the smoothed edge sums
	 */
	public static Pair<double[],double[]> smoothEdgeSums(Pair<double[],double[]> edge_sums, int filter_width, double filter_sigma)
	{
		Pair<double[],double[]> smoothed_sums = new Pair<double[],double[]>();
		double[] filter ;
		
		filter = MatrixUtility.fgaussian(filter_width, filter_sigma);
		smoothed_sums.first = MatrixUtility.conv(edge_sums.first, filter);
		smoothed_sums.second = MatrixUtility.conv(edge_sums.second, filter);
	
		//Debug: save smoothed edge sums
		if(false){			
			MatrixUtility.save("tmp/smoothed_horizontal_sums.txt", smoothed_sums.first);
			MatrixUtility.save("tmp/smoothed_vertical_sums.txt", smoothed_sums.second);
		}
		
		return smoothed_sums;
	}
	
	/**
	 * Smooth the given edge sums.
	 * @param edge_sums the edge sums
	 * @return the smoothed edge sums
	 */
	public static Pair<double[],double[]> smoothEdgeSums(Pair<double[],double[]> edge_sums)
	{
		//return smoothEdgeSums(edge_sums, 9, 2);
		return smoothEdgeSums(edge_sums, 15, 5);
	}

	/**
	 * Calculate the total edge sum response for the given horizontal or vertical lines.
	 * @param lines a vector of horizontal/vertical line locations
	 * @param edge_sums horizontal/vertical edge sums
	 * @return the edge sum response for the given lines
	 */
	public static double edgeResponse_old(Vector<Integer> lines, double[] edge_sums)
	{
		double response = 0;
		
		for(int i=0; i<lines.size(); i++){
			if(lines.get(i) >= 0 && lines.get(i) < edge_sums.length){
				response += edge_sums[lines.get(i)];
			}
		}
		
		return response;
	}

	  /**
     * Calculate the total edge sum response for the given horizontal or vertical lines.
     * @param lines a vector of horizontal/vertical line locations
     * @param edge_sums horizontal/vertical edge sums
     * @return the edge sum response for the given lines
     */
    public static double edgeResponse(Vector<Integer> lines, double[] edge_sums)//change: old func marked as _old
    {
        double response = 0;
        int index;
        double res;
        for(int i=0; i<lines.size(); i++){
            index=lines.get(i);
            if(index >= 0 && index < edge_sums.length){
                res=edge_sums[index];
                if(index-1>=0)
                    res=Math.max(res, edge_sums[index-1]);
                if(index+1<edge_sums.length)
                    res=Math.max(res, edge_sums[index+1]);
               
                response += res;
            }
        }
       
        return response;
    }

	
	
	/**
	 * Compute the distance between two vectors of locations greedily enforcing a one to one mapping.
	 * @param a a vector of locations
	 * @param b a vector of locations
	 * @return the shortest distance between the two vectors
	 */
	public static int greedyDistance(Vector<Integer> a, Vector<Integer> b)
	{
		int dist = 0;
		int[][] d = new int[a.size()][b.size()];
		Vector<Triple<Integer,Integer,Integer>> triples = new Vector<Triple<Integer,Integer,Integer>>();
		boolean[] amarks = new boolean[a.size()];
		boolean[] bmarks = new boolean[b.size()];
		int i, j;
		
		for(i=0; i<a.size(); i++){
			for(j=0; j<b.size(); j++){
				d[i][j] = (int)Math.abs(a.get(i)-b.get(j));
				triples.add(new Triple<Integer,Integer,Integer>(d[i][j], i, j));
			}
		}
		
		Collections.sort(triples);
		
		for(int k=0; k<triples.size(); k++){
			i = triples.get(k).second;
			j = triples.get(k).third;
			
			if(!amarks[i] && !bmarks[j]){
				amarks[i] = true;
				bmarks[j] = true;
				dist += triples.get(k).first;
			}
		}
		
		//Penalize unused lines
		if(false){
			double penalty = 10;
			
			for(i=0; i<amarks.length; i++){
				if(!amarks[i]) dist += penalty;
			}
			
			for(i=0; i<bmarks.length; i++){
				if(!bmarks[i]) dist += penalty;
			}
		}
		
		return dist;
	}

	/**
	 * Used dynamic time warping to compute the distance between the two vectors of locations.
	 * @param a a vector of locations
	 * @param b a vector of locations
	 * @return the shortest distance between the two vectors
	 */
	public static int dtwDistance(Vector<Integer> a, Vector<Integer> b)
	{
		int[][] d = new int[a.size()+1][b.size()+1];
		int d0, d1, d2, tmpd;
		
		//Initialize
		d[0][0] = 0;
		
		for(int i=1; i<=a.size(); i++){
			d[i][0] = Integer.MAX_VALUE;
		}
		
		for(int j=1; j<=b.size(); j++){
			d[0][j] = Integer.MAX_VALUE;
		}
		
		//Fill in table
		for(int i=1; i<=a.size(); i++){
			for(int j=1; j<=b.size(); j++){
				tmpd = Math.abs(a.get(i-1)-b.get(j-1));
				d0 = d[i-1][j];			//Deletion
				d1 = d[i][j-1];			//Insertion
				d2 = d[i-1][j-1];		//Match/Substitution
				
				d[i][j] = tmpd + Math.min(Math.min(d0, d1), d2);
			}
		}
		
		return d[a.size()][b.size()];
	}
	
	/**
	 * Match lines extracted from an image to a template (I = aT + b).
	 * @param template_lines the template
	 * @param image_lines the image extracted lines
	 * @param max_translation the maximum allowed translation
	 * @param min_scale the minimum allowed scale
	 * @param max_scale the maximum allowed scale
	 * @param edge_sums the edge sums (can be null)
	 * @return the template aligned to the extracted lines
	 */
	public static Vector<Integer> matchLines(Vector<Integer> template_lines, Vector<Integer> image_lines, int max_translation, double min_scale, double max_scale, double[] edge_sums)
	{
		Vector<Integer> lines = new Vector<Integer>();
		int cost, min_cost = Integer.MAX_VALUE;
		double mina = 1, minb = 0;
		double a, b;
	
		for(int t0=0; t0<template_lines.size(); t0++){
//			System.out.print(".");
			
			for(int i0=0; i0<image_lines.size(); i0++){				
				if(Math.abs(template_lines.get(t0)-image_lines.get(i0)) < max_translation){		//Check offset before continuing
					for(int t1=0; t1<template_lines.size(); t1++){
						for(int i1=0; i1<image_lines.size(); i1++){
							a = (image_lines.get(i1)-image_lines.get(i0)) / (double)(template_lines.get(t1)-template_lines.get(t0));
							b = -a * template_lines.get(t0) + image_lines.get(i0);
								
							if(a > min_scale && a < max_scale && Math.abs(b) < max_translation){
								lines.clear();
								
								for(int i=0; i<template_lines.size(); i++){
									lines.add((int)Math.round(a*template_lines.get(i) + b));
								}
								
								if(edge_sums != null){
									cost = -(int)Math.round(edgeResponse(lines, edge_sums));
								}else{
									//cost = greedyDistance(lines, image_lines);
									cost = dtwDistance(lines, image_lines);
								}
								
								if(cost < min_cost){
									min_cost = cost;
									mina = a;
									minb = b;
								}
							}
						}
					}
				}
			}
		}
		
//		System.out.println("\nScale/Translation: " + mina + ", " + minb);
		
		//Use optimal transformation to map template lines to the image
		lines.clear();
		
		for(int i=0; i<template_lines.size(); i++){
			lines.add((int)Math.round(mina*template_lines.get(i) + minb));
		}
				
		return lines;
	}
	
	/**
	 * Match lines extracted from an image to a template (I = aT + b).
	 * @param template_lines the template
	 * @param image_lines the image extracted lines
	 * @param max_translation the maximum allowed translation
	 * @param min_scale the minimum allowed scale
	 * @param max_scale the maximum allowed scale
	 * @return the template aligned to the extracted lines
	 */
	public static Vector<Integer> matchLines(Vector<Integer> template_lines, Vector<Integer> image_lines, int max_translation, double min_scale, double max_scale)
	{
		return matchLines(template_lines, image_lines, max_translation, min_scale, max_scale, null);
	}

	/**
	 * Draw horizontal/vertical lines to an image.
	 * @param image the image to draw to
	 * @param horizontal_lines the y coordinates of horizontal lines
	 * @param vertical_lines the x coordinates of vertical lines
	 * @param color the line color
	 * @param thickness the thickness of the lines (should be an odd value)
	 */
	public static void drawLines(int[][] image, Vector<Integer> horizontal_lines, Vector<Integer> vertical_lines, int color, int thickness)
	{
		int height = image.length;
		int width = image[0].length;
		int half_thickness = (thickness-1) / 2;
		int x, y;
		int minx, maxx, miny, maxy;
		
		//Draw horizontal lines
		if(horizontal_lines != null){
			for(int i=0; i<horizontal_lines.size(); i++){
				y = horizontal_lines.get(i);
				miny = y - half_thickness;
				maxy = y + half_thickness;
				if(miny < 0) miny = 0;
				if(maxy >= height) maxy = height-1;
				
				for(int v=miny; v<=maxy; v++){
					for(x=0; x<width; x++){
						image[v][x] = color;
					}
				}
			}
		}
		
		//Draw vertical lines
		if(vertical_lines != null){
			for(int i=0; i<vertical_lines.size(); i++){
				x = vertical_lines.get(i);
				minx = x - half_thickness;
				maxx = x + half_thickness;
				if(minx < 0) minx = 0;
				if(maxx >= width) maxx = width-1;
				
				for(int u=minx; u<=maxx; u++){
					for(y=0; y<height; y++){
						image[y][u] = color;
					}
				}
			}
		}
	}
	
	/**
	 * Draw horizontal/vertical lines to an image.
	 * @param image the image to draw to
	 * @param lines horizontal/vertical lines
	 * @param color the line color
	 * @param thickness the thickness of the lines (should be an odd value)
	 */
	public static void drawLines(int[][] image, Pair<Vector<Integer>,Vector<Integer>> lines, int color, int thickness)
	{
		drawLines(image, lines.first, lines.second, color, thickness);
	}
	
	/**
	 * Scale the given horizontal/vertical lines.
	 * @param lines the horizontal/vertical lines
	 * @param scale the scale factor
	 * @return the scaled horizontal/vertical lines
	 */
	public static Pair<Vector<Integer>,Vector<Integer>> scaleLines(Pair<Vector<Integer>,Vector<Integer>> lines, double scale)
	{
		Vector<Integer> scaled_horizontal_lines = new Vector<Integer>();
		Vector<Integer> scaled_vertical_lines = new Vector<Integer>();
		
		//Scale horizontal lines
		for(int i=0; i<lines.first.size(); i++){
			scaled_horizontal_lines.add((int)Math.round(scale*lines.first.get(i)));
		}
		
		//Scale vertical lines
		for(int i=0; i<lines.second.size(); i++){
			scaled_vertical_lines.add((int)Math.round(scale*lines.second.get(i)));
		}
		
		return new Pair<Vector<Integer>,Vector<Integer>>(scaled_horizontal_lines, scaled_vertical_lines);
	}
	
	/**
	 * Save horizontal/vertical lines to a file.
	 * @param filename the name of the file to save to
	 * @param lines the horizontal/vertical lines
	 */
	public static void saveLines(String filename, Pair<Vector<Integer>,Vector<Integer>> lines)
	{
		Vector<Integer> horizontal_lines = lines.first;
		Vector<Integer> vertical_lines = lines.second;
		
    try{    
      BufferedWriter outs = new BufferedWriter(new FileWriter(filename));
      
      for(int i=0; i<horizontal_lines.size(); i++){
        outs.write(horizontal_lines.get(i) + " ");
      }
        
      outs.newLine();
      
      for(int i=0; i<vertical_lines.size(); i++){
        outs.write(vertical_lines.get(i) + " ");
      }
      
      outs.close();
    }catch(Exception e){e.printStackTrace();}
	}
	
	/**
	 * Load horizontal/vertical lines from a file
	 * @param filename the name of the file to load from
	 * @return the horizontal/vertical lines
	 */
	public static Pair<Vector<Integer>,Vector<Integer>> loadLines(String filename)
	{
		Vector<Integer> horizontal_lines = new Vector<Integer>();
		Vector<Integer> vertical_lines = new Vector<Integer>();
		
		try{
			Scanner file = new Scanner(new File(filename));
			Scanner line = new Scanner(file.nextLine());
			
			while(line.hasNextInt()){
				horizontal_lines.add(line.nextInt());
			}
			
			line = new Scanner(file.nextLine());
			
			while(line.hasNextInt()){
				vertical_lines.add(line.nextInt());
			}
		}catch(Exception e){e.printStackTrace();}
		
		//Make sure the line positions are sorted
		Collections.sort(horizontal_lines);
		Collections.sort(vertical_lines);
		
		return new Pair<Vector<Integer>,Vector<Integer>>(horizontal_lines, vertical_lines);
	}
	
	


		public static double[] SigmoidalContrast(int[][] img, boolean enhance_contrast, int contrast, int midpoint, boolean sharpen){  	
			int h = img.length;
			int w = img[0].length;
			int[] img_c = new int[w*h];
		  	double[] img_g = new double[w*h];
		  	double[] channel = new double[w*h];
		  	int[] sigmoidal_map = new int[256];
			double total_before=0, total_after=0;
		  	int rgb;
		  	int red, green, blue, alpha;  
		  	int red_s, green_s, blue_s, alpha_s;
		  	
		  	double midpoint_d = 255.0*midpoint/100.0;		  	
		  	
		  	for(int i=0; i<255;i++){
		  		if(enhance_contrast){
		  			sigmoidal_map[i]= (int)(255.0*((1.0/(1.0+Math.pow(Math.E,contrast*(midpoint_d/255.0-
		  		            (double) i/255.0))))-(1.0/(1.0+Math.pow(Math.E,contrast*(midpoint_d/
		  		            (double) 255.0)))))/((1.0/(1.0+Math.pow(Math.E,contrast*(midpoint_d/
		  		            (double) 255.0-1.0))))-(1.0/(1.0+Math.pow(Math.E,contrast*(midpoint_d/
		  		            (double) 255.0)))))+0.5);
		  		}
		  		else{
		  			sigmoidal_map[i]= (int)(255.0*((1.0/255.0)*midpoint_d-Math.log((1.0-(1.0/(1.0+Math.pow(Math.E,midpoint_d/
		  			        (double) 255.0*contrast))+((double) i/255.0)*((1.0/
		  			        (1.0+Math.pow(Math.E,contrast*(midpoint_d/(double) 255.0-1.0))))-(1.0/
		  			        (1.0+Math.pow(Math.E,midpoint_d/(double) 255.0*contrast))))))/
		  			        (1.0/(1.0+Math.pow(Math.E,midpoint_d/(double) 255.0*contrast))+
		  			        ((double) i/255.0)*((1.0/(1.0+Math.pow(Math.E,contrast*(midpoint_d/
		  			        (double) 255.0-1.0))))-(1.0/(1.0+Math.pow(Math.E,midpoint_d/
		  			        (double) 255.0*contrast))))))/contrast));
		  		}
		  	}
		  	
		  	
		  	for(int x=0; x<w; x++){
		  		for(int y=0; y<h; y++){
		  			rgb = img[y][x];
		  			
		    		alpha = (rgb>>24) & 0x000000ff;
		    		red = (rgb>>16) & 0x000000ff;
		    		green = (rgb>>8) & 0x000000ff;
		    		blue = rgb & 0x000000ff;
			  		
		    		total_before+=((red + green + blue)/3.0)/255.0;
//		    		total_before+=(0.3 * red + 0.59 * green + 0.11 * blue)/255.0;
		    		red_s=sigmoidal_map[red];
		    		green_s=sigmoidal_map[green];
		    		blue_s=sigmoidal_map[blue];
		    		alpha_s=sigmoidal_map[alpha];
		    		
		    		img_c[y*w+x] = (alpha_s << 24) | (red_s << 16) | (green_s << 8) | blue_s;
		  		}  	
		  	}
		  	
		  	

		  	
		  	
		  	
		  	if (sharpen){
		  	
		  		double[][] kernel = new double[][]{{-1.9641280346397447E-5, -2.392797792004707E-4, -0.0010723775711956548, -0.001768051711852017, -0.0010723775711956548, -2.392797792004707E-4, -1.9641280346397447E-5}, {-2.392797792004707E-4, -0.0029150244650281943, -0.013064233284684923, -0.02153927930184863, -0.013064233284684923, -0.0029150244650281943, -2.392797792004707E-4}, {-0.0010723775711956548, -0.013064233284684923, -0.05854983152431917, -0.09653235263005391, -0.05854983152431917, -0.013064233284684923, -0.0010723775711956548}, {-0.001768051711852017, -0.02153927930184863, -0.09653235263005391, 1.9989175836526734, -0.09653235263005391, -0.02153927930184863, -0.001768051711852017}, {-0.0010723775711956548, -0.013064233284684923, -0.05854983152431917, -0.09653235263005391, -0.05854983152431917, -0.013064233284684923, -0.0010723775711956548}, {-2.392797792004707E-4, -0.0029150244650281943, -0.013064233284684923, -0.02153927930184863, -0.013064233284684923, -0.0029150244650281943, -2.392797792004707E-4}, {-1.9641280346397447E-5, -2.392797792004707E-4, -0.0010723775711956548, -0.001768051711852017, -0.0010723775711956548, -2.392797792004707E-4, -1.9641280346397447E-5}};
	
	//    		int j=(int) 3.5;
	//    		int line=0, col=0;
	//    		double normalize=0;
	//    		   for (int v=(-j); v <= j; v++)
	//    		   {
	//    		     for (int u=(-j); u <= j; u++)
	//    		     {
	//    		       kernel[line][col]=(double) (-Math.pow(Math.E, -((double) u*u+v*v)/(2.0*dev*dev))/(2.0*Math.PI*dev*dev));
	//    		      // System.out.println("v: "+v+" u: "+u+" - "+kernel[line][col]);
	//    		       normalize+=kernel[line][col];
	//    		       col++;
	//    		     }
	//    		     col=0;
	//    		     line++;
	//    		   }
	//
	//    		kernel[3][3]=(-2.0)*normalize;
	//    		System.out.println(kernel[3][3]);
	
	//    		r=ImageUtility.convolve(r, w, h, kernel);
	//    		g=ImageUtility.convolve(g, w, h, kernel);
	//    		b=ImageUtility.convolve(b, w, h, kernel);
	    		
		  		for(int i=0; i<w*h;i++){
	    			img_g[i]=0;
	    		}
	
		  		for(int i=0; i<w*h;i++){
	    			channel[i]=(img_c[i]>>16) & 0x000000ff;
	    		}
		  		channel=ImageUtility.convolve(channel, w, h, kernel);
		  		for(int i=0; i<w*h;i++){
	    			img_g[i]+=channel[i];
	    		}
		  		
		  		for(int i=0; i<w*h;i++){
	    			channel[i]=(img_c[i]>>8) & 0x000000ff;
	    		}
		  		channel=ImageUtility.convolve(channel, w, h, kernel);
		  		for(int i=0; i<w*h;i++){
	    			img_g[i]+=channel[i];
	    		}
		  		
		  		for(int i=0; i<w*h;i++){
	    			channel[i]= img_c[i] & 0x000000ff;
	    		}
		  		channel=ImageUtility.convolve(channel, w, h, kernel);
		  		for(int i=0; i<w*h;i++){
	    			img_g[i]+=channel[i];
	    		}
		  	}
		  	else{
		  		for(int i=0; i<w*h;i++){
	    			img_g[i]=0;
	    		}
	
		  		for(int i=0; i<w*h;i++){
	    			img_g[i]+=(img_c[i]>>16) & 0x000000ff;
	    		}
		  		
		  		for(int i=0; i<w*h;i++){
	    			img_g[i]+=(img_c[i]>>8) & 0x000000ff;
	    		}

		  		for(int i=0; i<w*h;i++){
	    			img_g[i]+= img_c[i] & 0x000000ff;
	    		}

		  	}

	  		for(int i=0; i<w*h;i++){
    			img_g[i]=(img_g[i]/255.0)/3.0;
    			total_after+=img_g[i];
    		}
	  		
	  				  	
		  	System.out.println("Before: "+total_before/(w*h));
		  	System.out.println("After : "+total_after/(w*h));
		  	return img_g;
		}

	  

		/**
		 * Get the rotation of a scanned grid (assumes rotated about center).
		 * @param max_angle the maximum angle that could be considered
		 * @return the angle of rotation
		 */
		public double getRotation_OLD(double max_angle)
		{
			Vector<Pair<Double,Double>> lines;
			Histogram<Double> histogram = new Histogram<Double>(Histogram.createDoubleBins(0, 1, 180));
			double theta;
					
			int threshold=(int)Math.round(0.2*width)+1;
			lines = JavaCVUtility.getLines(image_g, width, height, 0.5, threshold);
			
			//Debug: show lines
			if(false){//(true && width>1000){//
//				System.out.println("threshold: "+threshold);
//				System.out.println("theta: "+0.5*Math.PI/180);
				int[] image_rgb1d = ImageUtility.to1D(image_rgb); //image_rgb1d = ImageUtility.g2argb(image_g, width, height);
				Vector<Pixel[]> line_segments = JavaCVUtility.getLineSegments(lines, width, height);
				
//				System.out.println("Lines: " + lines.size());
				ImageUtility.drawLines(image_rgb1d, width, height, line_segments, 0x000000ff, 2);		
				ImageViewer viewer = ImageViewer.show(image_g, width, height, 1200, "Lines");
				viewer.add(image_rgb1d, width, height, true);
//				ImageUtility.save("tmp/output_lines.jpg", ImageUtility.to2D(image_rgb1d, width, height));
			}
			
			//Determine rotation based on found lines and un-rotate the image		
			for(int i=0; i<lines.size(); i++){
				histogram.add(lines.get(i).second * 180/Math.PI);
			}
			
			if(false){//(true && width>1000){//
				for(int i=0; i<180; i++)
					System.out.println(i+": "+histogram.get(i*1.0));
				
				System.out.println("MAX: "+histogram.getMax());
				System.out.println("MAX AVG: "+Histogram.mean(histogram.getValues(histogram.getMax())));
			}
			
			
			int min_limit = (int)(90-max_angle);
			int max_limit = (int)(90+max_angle);
			double max=90; 
			double max_val=0;
			for(int i=min_limit; i<max_limit; i++){
				if(histogram.get(i*1.0)>max_val){
					max=i;
					max_val=histogram.get(max);
				}
			}
			
			theta = Histogram.mean(histogram.getValues(max));
			theta = 90 - theta;

			return theta;
		}
	
	/**
	 * Extract cell locations from an imaged grid.
	 * @param Irgb an image containing the grid
	 * @param template_lines the template lines
	 * @return the cell locations
	 */
	public static CellLocation[][] getCellLocations(int[][] Irgb, Pair<Vector<Integer>,Vector<Integer>> template_lines, boolean resize_template, String state)
	{
		int rows = template_lines.first.size() - 1;
		int columns = template_lines.second.size() - 1;
		CellLocation[][] cells = new CellLocation[rows][columns];
		Pair<Vector<Integer>,Vector<Integer>> mapped_lines;
		ImagedGrid image;
		double theta;
		
		image = new ImagedGrid(Irgb);			

		
		image.scale(0.25);

		image.thin();

		theta = image.unrotate(10); 
		System.out.println("Finished unrotating image by "+theta);
		
		mapped_lines = scaleLines(image.getGridLines(template_lines, true, resize_template, state), 4);
		
		image = new ImagedGrid(Irgb, image.threshold);
//		image = new ImagedGrid(Irgb);

		for(int r=0; r<rows; r++){
			for(int c=0; c<columns; c++){
//				image.getCell(theta, mapped_lines, r, c);
				//census threshold
//				cells[r][c] = image.getRefinedCellLocation(theta, mapped_lines, r, c, 4, 0.2, image.threshold);
				cells[r][c] = image.getRefinedCellLocation(theta, mapped_lines, r, c, 4, 0.2);
			}
		}
		
		return cells;
	}
	
	
	
	
	
	/**
	 * A function to run debug tests.
	 */
	public static void debug()
	{

		if(false){
			int[][] image = ImageUtility.load("C:/Users/kmchenry/Files/Data/NARA/DataSets/1930Census-ChampaignCounty/illinoiscensus00reel410_0005.jpg");
			CellLocation cell = new CellLocation();
			cell.set(1000, 100, 1760, 1540);
			ImageViewer.show(cell.get(image), "Debug");
		}
		
		if(true){
			int[][] image;
			Pair<Vector<Integer>,Vector<Integer>> template_lines;
			int column;
			
			if(false){
				image = load("C:/Users/kmchenry/Files/Data/NARA/DataSets/1930Census-ChampaignCounty/illinoiscensus00reel410_0005.jpg");
				template_lines = loadLines("tmp/template_lines_IL.txt");
				column = 11;
			}else if(false){
				image = load("C:/Users/kmchenry/Files/Data/NARA/DataSets/1930Census-Misc/Hawaii/0004.jp2");
				template_lines = loadLines("tmp/template_lines_HI.txt");
				column = 5;
			}else{
				int h,w;
//				image = load("/home/liana/convert/images/North_Carolina/1700/jp2/0100.jp2");//load("/home/liana/convert/images/1678/jp2/0823_scs.jp2");//("tmp/NC/0427.jpg");
//				template_lines = loadLines("tmp/template_lines_NC.txt");//("tmp/template_lines_IL.txt");//
//				image = load("/home/liana/convert/images/2484/jp2/0030.jp2");//load("/home/liana/convert/images/1678/jp2/0823_scs.jp2");//("tmp/NC/0427.jpg");
//				template_lines = loadLines("tmp/template_lines_WA.txt");//("tmp/template_lines_IL.txt");//
//				image = load("/home/liana/convert/images/American_Samoa/2629/jp2/0950.jp2");//load("/home/liana/convert/images/1678/jp2/0823_scs.jp2");//("tmp/NC/0427.jpg");
//				template_lines = loadLines("tmp/template_lines_AS.txt");//("tmp/template_lines_IL.txt");//
//				image = load("/home/liana/convert/images/405/jp2/0005.jp2");//load("/home/liana/convert/images/1678/jp2/0823_scs.jp2");//("tmp/NC/0427.jpg");
//				image = load("/home/liana/convert/images/District_of_Columbia/293/jp2/0008.jp2");//load("/home/liana/convert/images/1678/jp2/0823_scs.jp2");//("tmp/NC/0427.jpg");
//				template_lines = loadLines("templates/template_lines_DC.txt");//("tmp/template_lines_IL.txt");//
//				image = load("/home/liana/convert/images/2634/jp2/0400.jp2");//load("/home/liana/convert/images/1678/jp2/0823_scs.jp2");//("tmp/NC/0427.jpg");
//				template_lines = loadLines("templates/template_lines_HI.txt");//("tmp/template_lines_IL.txt");//
//				image = load("/home/liana/convert/images/Alaska/2626/jp2/1000.jp2");//load("/home/liana/convert/images/1678/jp2/0823_scs.jp2");//("tmp/NC/0427.jpg");
//				template_lines = loadLines("templates/template_lines_AL.txt");//("tmp/template_lines_IL.txt");//
//				image = load("/home/liana/convert/images/Vermont/2426/jp2/0450.jp2");//load("/home/liana/convert/images/1678/jp2/0823_scs.jp2");//("tmp/NC/0427.jpg");
//				image = load("/home/liana/convert/images/Arizona/61/jp2/0400.jp2");//load("/home/liana/convert/images/1678/jp2/0823_scs.jp2");//("tmp/NC/0427.jpg");
//				image = load("/home/liana/convert/images/Delaware/289/jp2/0800.jp2");//load("/home/liana/convert/images/1678/jp2/0823_scs.jp2");//("tmp/NC/0427.jpg");
//				template_lines = loadLines("templates/template_lines_AZ.txt");//("tmp/template_lines_IL.txt");//
				column = 7;
				
				
			}	
			String state_code;
//			for(int i=0; i<3;i++){
//			image = load("/home/liana/Desktop/AS/m-t0627-04645/m-t0627-04645-00050.jpg");
//			template_lines = loadLines("/home/liana/Desktop/AS_1940_4500_3584.txt");
//			state_code="AS_1940";
//			image = load("/home/liana/Desktop/AK/m-t0627-04578/m-t0627-04578-01246.jpg");
//			template_lines = loadLines("/home/liana/Desktop/AK_1940_7620_4592.txt");
//			state_code="AK_1940";
			
//			image = load("/Users/liana/Census/input/NC/m-t0627-02876/m-t0627-02876-00005.jpg");
//			template_lines = loadLines("/Users/liana/Documents/workspace-census-extr/CensusSectionSegmentor/templates/1930/template_lines_NC.txt");
//			state_code="1930_NC";
			image = load("/Users/liana/Desktop/javaconfig/HelloCV/img/m-t0627-00889-00141.jpg");
			template_lines = loadLines("/Users/liana/Documents/workspace-census-extr/CensusSectionSegmentor/templates/1940/template_lines_DEF.txt");
			state_code="_1940";
			
			long t0 = System.currentTimeMillis();
			CellLocation[][] cells = getCellLocations(image, template_lines, true, state_code);
			System.out.println("Elapsed time: " + ((System.currentTimeMillis()-t0)/1000.0) + " s");
//			}
			
			ImageViewer viewer = new ImageViewer("Grid Cells", 200);
			
			for(int r=0; r<cells.length; r++){
				viewer.add(cells[r][column].get(image), -1, -1, true);
			}
			
		}
		

		//Sit here and don't return
		while(true){
			Utility.pause(10000);
		}
	}
	
	/**
	 * A main for debug purposes.
	 * @param args the command line arguments
	 */
	public static void main(String args[])
	{		
		String filename = null;
		String template = null;
		ImagedGrid image;
		Pair<Vector<Integer>,Vector<Integer>> lines;
		double theta;
		int rows, columns;
		int row = -1;
		int column = -1;
		boolean REFINE = false;
		boolean PROCESS = false;
		boolean LABEL = false;
		long t0 = System.currentTimeMillis();

		debug();
		
		//Default arguments
		if(args.length == 0){
			//args = new String[]{"-c", "5", "-refine", "-template", "tmp/template_lines_IL.txt", "C:/Users/kmchenry/Files/Data/NARA/DataSets/1930Census-ChampaignCounty/illinoiscensus00reel410_0005.jpg"};
			//args = new String[]{"-c", "11", "-refine", "-template", "tmp/template_lines_IL.txt", "C:/Users/kmchenry/Files/Data/NARA/DataSets/1930Census-ChampaignCounty/illinoiscensus00reel410_0175.jpg"};
			args = new String[]{"-c", "5", "-template", "tmp/template_lines_HI.txt", "C:/Users/kmchenry/Files/Data/NARA/DataSets/1930Census-Misc/Hawaii/0004.jp2"};
		}
		
		//Process command line arguments
		for(int i=0; i<args.length; i++){
			if(args[i].equals("-?")){
				System.out.println("Usage: ImagedGrid [options] [filename]");
				System.out.println();
				System.out.println("Options: ");
				System.out.println("  -?: display this help");
				System.out.println("  -r: the row to display");
				System.out.println("  -c: the column to display");
				System.out.println("  -process: post process cells after retrieval");
				System.out.println("  -refine: refine cell boundaries during retrieval");
				System.out.println("  -template: the template file to use");
				System.out.println("  -label: manually label the grid lines");
				System.out.println();
				System.exit(0);
			}else if(args[i].equals("-r")){
				row = Integer.valueOf(args[++i]);
			}else if(args[i].equals("-c")){
				column = Integer.valueOf(args[++i]);
			}else if(args[i].equals("-process")){
				PROCESS = true;	
			}else if(args[i].equals("-refine")){
				REFINE = true;
			}else if(args[i].equals("-template")){
				template = args[++i];
			}else if(args[i].equals("-label")){
				LABEL = true;
			}else{
				filename = args[i];
			}
		}
		
		//Segment image
		image = new ImagedGrid(filename);
		
		if(row >= 0 || column >= 0){
			ImageViewer viewer = new ImageViewer("Grid Cells", 1000);
			Object cell = null;
			int w = -1, h = -1;
			
			theta = Double.valueOf(Utility.loadToString("tmp/theta.txt"));
			lines = loadLines("tmp/mapped_lines.txt");
			rows = lines.first.size() - 1;
			columns = lines.second.size() - 1;
			
			if(row >= 0 && column >= 0){
				if(REFINE){
					cell = image.getRefinedCell(theta, lines, row, column);
				}else{
					cell = image.getCell(theta, lines, row, column);
				}
				
				if(PROCESS){
					h = ((int[][])cell).length; w = ((int[][])cell)[0].length;
					cell = image.postProcess((int[][])cell);
				}
				
				viewer.add(cell, w, h, true);
			}else if(row == -1 && column >= 0){
				for(int i=0; i<rows; i++){
					if(REFINE){
						cell = image.getRefinedCell(theta, lines, i, column);
					}else{
						cell = image.getCell(theta, lines, i, column);
					}
					
					if(PROCESS){
						h = ((int[][])cell).length; w = ((int[][])cell)[0].length;
						cell = image.postProcess((int[][])cell);
					}
					
					viewer.add(cell, w, h, true);
				}
			}else if(row >= 0 && column == -1){
				for(int i=0; i<rows; i++){
					if(REFINE){
						cell = image.getRefinedCell(theta, lines, row, i);
					}else{
						cell = image.getCell(theta, lines, row, i);
					}
					
					if(PROCESS){
						h = ((int[][])cell).length; w = ((int[][])cell)[0].length;
						cell = image.postProcess((int[][])cell);
					}
					
					viewer.add(cell, w, h, true);
				}
			}	
		}else{
			image.scale(0.25);
			image.thin();			
			theta = image.unrotate(30);
			//image.show();
			
			if(LABEL){
				saveLines("tmp/template_lines.txt", image.labelGridLines());
			}else{	
				Utility.save("tmp/theta.txt", Double.toString(theta));
				saveLines("tmp/mapped_lines.txt", scaleLines(image.getGridLines(template, false, ""), 4));
			}
		}
		
		System.out.println("Elapsed time: " + ((System.currentTimeMillis()-t0)/1000.0) + " s");
	}
}