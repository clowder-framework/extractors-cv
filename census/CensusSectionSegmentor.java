package edu.illinois.ncsa.medici.census;

import java.io.BufferedReader;
import java.io.DataOutputStream;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.text.DateFormat;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;
import java.util.Properties;
import java.io.FileInputStream;
import java.io.FileNotFoundException;

import java.awt.geom.AffineTransform;

import org.apache.commons.io.FileUtils;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;

import org.apache.http.HttpEntity;
import org.apache.http.HttpResponse;
import org.apache.http.HttpVersion;
import org.apache.http.client.HttpClient;
import org.apache.http.client.methods.HttpPost;
import org.apache.http.entity.mime.MultipartEntityBuilder;
import org.apache.http.entity.mime.content.ContentBody;
import org.apache.http.entity.mime.content.FileBody;
import org.apache.http.impl.client.DefaultHttpClient;
import org.apache.http.params.CoreProtocolPNames;
import org.apache.http.util.EntityUtils;

import org.json.JSONObject;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.rabbitmq.client.AMQP;
import com.rabbitmq.client.Channel;
import com.rabbitmq.client.Connection;
import com.rabbitmq.client.ConnectionFactory;
import com.rabbitmq.client.DefaultConsumer;
import com.rabbitmq.client.Envelope;

public class CensusSectionSegmentor {
    private static Log logger = LogFactory.getLog(CensusSectionSegmentor.class);

    // ----------------------------------------------------------------------
    // BEGIN CONFIGURATION
    // ----------------------------------------------------------------------

    // name where rabbitmq is running
    private static String rabbitmqHost;

    // name to show in rabbitmq queue list
    private static String exchange;

    // name to show in rabbitmq queue list
    private static String extractorName;

    // username and password to connect to rabbitmq
    private static String rabbitmqUsername;
    private static String rabbitmqPassword;

    // accept any type of file that is text
    private static String messageType;


    // ----------------------------------------------------------------------
    // END CONFIGURATION
    // ----------------------------------------------------------------------

    private static String templatePath;
    private static String templateState;
    private static String templateYear;

    private static Pair<Vector<Integer>, Vector<Integer>> templateLines;


    DateFormat dateformat = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSXXX");
    ObjectMapper mapper = new ObjectMapper();

    /**
     * Main function, setup a connection and wait for messages.
     * 
     * @param argv
     *            command line arguments, not used.
     * @throws Exception
     *             if no connection could be made to the messagebus.
     */
    public static void main(String[] argv) throws Exception {
        
        Properties props = new Properties();
        FileInputStream in;
        try {
            in = new FileInputStream("config.properties");
            props.load(in);
            in.close();
        } catch (FileNotFoundException e) {
            // TODO Auto-generated catch block
            e.printStackTrace();
        } catch (IOException e) {
            // TODO Auto-generated catch block
            e.printStackTrace();
        }
        

        // name where rabbitmq is running
        rabbitmqHost = props.getProperty("rabbitmqHost");

        // name to show in rabbitmq queue list
        exchange = props.getProperty("exchange");

        // name to show in rabbitmq queue list
        extractorName = props.getProperty("extractorName");

        // username and password to connect to rabbitmq
        rabbitmqUsername = props.getProperty("rabbitmqUsername");
        rabbitmqPassword = props.getProperty("rabbitmqPassword");

        // accept any type of file that is text
        messageType = props.getProperty("messageType");
        

        //Census specific configs        

        // the path to the template file to be used
        templatePath = props.getProperty("templatePath");

        //the state of the template used
        templateState = props.getProperty("templateState");

        //the year of the template used
        templateYear = props.getProperty("templateYear");


        //load the template lines that will be used to segment all forms received
        templateLines = ImagedGrid.loadLines(templatePath);



        // setup connection parameters
        ConnectionFactory factory = new ConnectionFactory();
        factory.setHost(rabbitmqHost);
        if ((rabbitmqUsername != null) && (rabbitmqPassword != null)) {
            factory.setUsername(rabbitmqUsername);
            factory.setPassword(rabbitmqPassword);
        }

        // connect to rabitmq
        Connection connection = factory.newConnection();

        // connect to channel
        final Channel channel = connection.createChannel();

        // declare the exchange
        channel.exchangeDeclare(exchange, "topic", true);

        // declare the queue
        channel.queueDeclare(extractorName, true, false, false, null);

        // connect queue and exchange
        channel.queueBind(extractorName, exchange, messageType);

        // create listener
        channel.basicConsume(extractorName, false, "", new DefaultConsumer(channel) {
            @Override
            public void handleDelivery(String consumerTag, Envelope envelope,
                    AMQP.BasicProperties header, byte[] body) throws IOException {
                CensusSectionSegmentor cseg = new CensusSectionSegmentor();
                cseg.onMessage(channel, envelope.getDeliveryTag(), header, new String(body));
            }
        });

        // start listening
        logger.info("[*] Waiting for messages. To exit press CTRL+C");
        while (true) {
            Thread.sleep(1000);
        }
    }

    /**
     * Processes a message received over the messagebus. This will first
     * download the file from medici, and then process the file sending back the
     * results of the processing.
     * 
     * @param channel
     *            the rabbitMQ channel to send messages over.
     * @param tag
     *            unique id associated with this message.
     * @param header
     *            the header of the incoming message, used for sending
     *            responses.
     * @param body
     *            the actual message to received over the messagebus.
     */
    public void onMessage(Channel channel, long tag, AMQP.BasicProperties header, String body) {
        File inputfile = null;
        String fileid = "";
        String secretKey = "";
        
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> jbody = mapper.readValue(body, Map.class);
            String host = jbody.get("host").toString();
            fileid = jbody.get("id").toString();
            secretKey = jbody.get("secretKey").toString();
            String intermediatefileid = jbody.get("intermediateId").toString();
            if (!host.endsWith("/")) {
                host += "/";
            }

            statusUpdate(channel, header, fileid, "Started processing file");

            // download the file
            inputfile = downloadFile(channel, header, host, secretKey, fileid, intermediatefileid);

            // process file
            processFile(channel, header, host, secretKey, fileid, intermediatefileid, inputfile);

        } catch (Throwable thr) {
            logger.error("Error processing file", thr);
            try {
                statusUpdate(channel, header, fileid, "Error processing file : " + thr.getMessage());
            } catch (IOException e) {
                logger.warn("Could not send status update.", e);
            }
        } finally {

            // send ack that we are done
            channel.basicAck(tag, false);

            try {
                statusUpdate(channel, header, fileid, "Done");
            } catch (IOException e) {
                logger.warn("Could not send status update.", e);
            }
            if (inputfile != null) {
                inputfile.delete();
            }
        }
    }

    /**
     * Sends a status update back to medici about the current status of
     * processing.
     * 
     * @param channel
     *            the rabbitMQ channel to send messages over
     * @param header
     *            the header of the incoming message, used for sending
     *            responses.
     * @param fileid
     *            the id of the file to be processed
     * @param status
     *            the actual message to send back using the messagebus.
     * @throws IOException
     *             if anything goes wrong.
     */
    private void statusUpdate(Channel channel, AMQP.BasicProperties header, String fileid,
            String status) throws IOException {
        logger.debug("[" + fileid + "] : " + status);

        Map<String, Object> statusreport = new HashMap<String, Object>();
        statusreport.put("file_id", fileid);
        statusreport.put("extractor_id", extractorName);
        statusreport.put("status", status);
        statusreport.put("start", dateformat.format(new Date()));

        AMQP.BasicProperties props = new AMQP.BasicProperties.Builder().correlationId(
                header.getCorrelationId()).build();
        channel.basicPublish('', header.getReplyTo(), props,
                mapper.writeValueAsBytes(statusreport));
    }

    /**
     * Reads the file from the medici server and stores it locally on disk.
     * 
     * @param channel
     *            the rabbitMQ channel to send messages over
     * @param header
     *            the header of the incoming message, used for sending
     *            responses.
     * @param host
     *            the remote host to connect to, including the port and
     *            protocol.
     * @param key
     *            the secret key used to access medici.
     * @param fileid
     *            the id of the file to be processed
     * @param intermediatefileid
     *            the actual id of the raw file data to process. return the
     *            actual file downloaded from the server.
     * @throws IOException
     *             if anything goes wrong.
     */
    private File downloadFile(Channel channel, AMQP.BasicProperties header, String host,
            String key, String fileid, String intermediatefileid) throws IOException {
        statusUpdate(channel, header, fileid, "Downloading file");

        URL source = new URL(host + "api/files/" + intermediatefileid + "?key=" + key);
        File outputfile = File.createTempFile("medici", ".tmp");
        outputfile.deleteOnExit();

        FileUtils.copyURLToFile(source, outputfile);
        return outputfile;
    }

    /**
     * Process the data. In this case it will count the number of lines, words
     * and characters in a text file.
     * 
     * @param channel
     *            the rabbitMQ channel to send messages over
     * @param header
     *            the header of the incoming message, used for sending
     *            responses.
     * @param host
     *            the remote host to connect to, including the port and
     *            protocol.
     * @param key
     *            the secret key used to access medici.
     * @param fileid
     *            the id of the file to be processed
     * @param intermediatefileid
     *            the actual id of the raw file data to process.
     * @param inputfile
     *            the actual file downloaded from the server.
     * @throws IOException
     *             if anything goes wrong.
     */
    private void processFile(Channel channel, AMQP.BasicProperties header, String host, String key,
            String fileid, String intermediatefileid, File inputfile) throws IOException {
        
        statusUpdate(channel, header, fileid, "Extracting Census cells from file.");

        int[][] subImage;
        double[] grayscaleSubImage;
        BufferedImage cellImage;
        

        //load the image to be processed
        int[][] form_img = ImagedGrid.load(inputfile.getAbsolutePath());

        long l = System.currentTimeMillis();
        CellLocation[][] cell_locations= ImagedGrid.getCellLocations(form_img, templateLines, true, templateState + "_" + templateYear);

        logger.info("SEGMENTATION : " + fileid + " " + ((System.currentTimeMillis() - l) / 1000.0));
        
        int rows = cell_locations.length;
        int cols = cell_locations[0].length;
                
        CellLocation cell;
        double m00, m01, m10, m11, tx, ty;
        double[] signature;
        File cellFile;
        FileOutputStream fos;
        Map<String, Object> cellMetadata;
        Map<String, Object> areaMetadata;
        Map<String, Object> previewMetadata;

        long feature = 0;
        long index = 0;
        
        float[] corners = new float[] { -0.5f, 0.5f, 0.5f, 0.5f, 0.5f, -0.5f, -0.5f, -0.5f };
        float[] cellcoords;
        AffineTransform trans


        l = System.currentTimeMillis();
        for(int col=0; col<cols; col++){
            for(int row=0; row<rows; row++){
                
                // feature extraction
                cell=cell_locations[row][col];
                
                m00 = cell.M[0][0];
                m01 = cell.M[0][1];
                m10 = cell.M[1][0];
                m11 = cell.M[1][1];
                tx = cell.M[0][2];
                ty = cell.M[1][2];
                
                subImage = cell.get(form_img);
                
                //buffered image for preview
                cellImage = ImageUtility.argb2image(subImage);
                
                grayscaleSubImage = ImageUtility.argb2g(subImage);
                
                //get signature Rath04 from grayscale image
                signature = WordSpotting.getSignature_Rath04(grayscaleSubImage, subImage[0].length, subImage.length);

                cellMetadata = new HashMap<String, Object>();
                cellMetadata.put("m00", m00);
                cellMetadata.put("m01", m01);
                cellMetadata.put("m10", m10);
                cellMetadata.put("m11", m11);
                cellMetadata.put("tx", tx);
                cellMetadata.put("ty", ty);
                cellMetadata.put("signature", signature);

                cellcoords = new float[corners.length];

                trans = new AffineTransform(m00, m10, m01, m11, tx, ty);       
                trans.transform(corners, 0, cellcoords, 0, 4);

                cellMetadata.put("x0", (int) cellcoords[0]);
                cellMetadata.put("y0", (int) cellcoords[1]);
                cellMetadata.put("x1", (int) cellcoords[2]);
                cellMetadata.put("y1", (int) cellcoords[3]);
                cellMetadata.put("x2", (int) cellcoords[4]);
                cellMetadata.put("y2", (int) cellcoords[5]);
                cellMetadata.put("x3", (int) cellcoords[6]);
                cellMetadata.put("y3", (int) cellcoords[7]);


                cellMetadata.put("file_id",fileid)

                int x = (int) cellcoords[0];
                int y = (int) cellcoords[1];
                int w = (int) (cellcoords[0]-cellcoords[2]));
                int h = (int) (cellcoords[1]-cellcoords[3]));

                areaMetadata = new HashMap<String, Object>();
                areaMetadata.put("x", x);
                areaMetadata.put("y", y);
                areaMetadata.put("w", w);
                areaMetadata.put("h", h);

                cellMetadata.put("area", areaMetadata);

                #upload section to medici
                sectionId=extractors.upload_section(sectiondata=secdata, parameters=parameters)

                # section preview image metadata
                previewMetadata = new HashMap<String, Object>();
                previewMetadata.put("section_id", sectionId);
                previewMetadata.put("width", w);
                previewMetadata.put("height", h);
                previewMetadata.put("extractor_id", extractorName);

                try{
                    fos = new FileOutputStream(cellfilename);
                    ImageIO.write(cellImage, "png", fos);
                    fos.flush();
                    fos.close();
                }catch(Exception e) {e.printStackTrace();}

                uploadPreview(channel, header, host, key, cellfilename, previewMetadata)

                try{
                    cellFile = new File(cellfilename);
                    if (cellFile != null && cellFile.exists()){
                        cellFile.delete();
                    }
                }catch(Exception e) {e.printStackTrace();}

                postSectionMetaData(host, key, fileid, cellMetadata);
                





            }
        }

        logger.info("CELLS METADATA POSTED : " + fileid + " " + ((System.currentTimeMillis() - l) / 1000.0));


    }

private String uploadPreview(Channel channel, AMQP.BasicProperties header, String host, String key,
            File previewfile, Map<String, Object> previewMetadata)
            throws IOException {

        String previewId = null;
        DefaultHttpClient httpclient = new DefaultHttpClient();
        HttpPost httpPost = new HttpPost(host + "api/previews?key=" + key);

        HttpEntity httpEntity = MultipartEntityBuilder.create()
            .addBinaryBody("file", previewfile, ContentType.create("image/png"), previewfile.getName())
            .build();

        httpPost.setEntity(httpEntity);          
        HttpResponse response = httpclient.execute(httpPost);
        
        // System.out.println(response.getStatusLine());                      
        HttpEntity idEntity = response.getEntity();

        JSONObject json = new JSONObject(EntityUtils.toString(idEntity));
        if (json.has("id")) {
            previewId =  json.getString("id");
        }

        //uploads preview metadata if exists
        if (previewMetadata != null){
            url = new URL(host + "api/previews/" + previewId + "/metadata?key=" + key);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json");//application/octet-stream
            conn.setDoOutput(true);

            DataOutputStream wr = new DataOutputStream(conn.getOutputStream());
            mapper.writeValue(wr, previewMetadata);
            wr.flush();
            wr.close();

            int responseCode = conn.getResponseCode();
            if (responseCode != 200) {
                throw (new IOException("Error uploading preview metadata [code=" + responseCode + "]"));
            }

            return previewId;

        }
}



    private String uploadSection(String host, String key, String fileid, Map<String, Object> metadata)
            throws IOException {
        String sectionId = null;
        URL url = new URL(host + "api/sections?key=" + key);

        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setRequestProperty("Content-Type", "application/json");
        conn.setDoOutput(true);

        DataOutputStream wr = new DataOutputStream(conn.getOutputStream());
        mapper.writeValue(wr, metadata);
        wr.flush();
        wr.close();

        int responseCode = conn.getResponseCode();
        if (responseCode != 200) {
            throw (new IOException("Error uploading metadata [code=" + responseCode + "]"));
        }

        BufferedReader in = new BufferedReader(new InputStreamReader(conn.getInputStream()));
        String inputLine;
        StringBuffer response = new StringBuffer();

        while ((inputLine = in.readLine()) != null) {
            response.append(inputLine);
        }
        in.close();

        JSONObject json = new JSONObject(response);
        if (json.has("id")) {
            sectionId =  json.getString("id");
        }

        return sectionId;
    }



    /**
     * Post a map as a json message to a medici URL. The response is returned as
     * a string.
     * 
     * @param host
     *            the remote host to connect to, including the port and
     *            protocol.
     * @param key
     *            the secret key used to access medici.
     * @param fileid
     *            the id of the file whose metadata is uploaded.
     * @param metadata
     *            the actual metadata to upload.
     * @return the reponse of the server as a string.
     * @throws IOException
     *             if anything goes wrong.
     */
    private String postMetaData(String host, String key, String fileid, Map<String, Object> metadata)
            throws IOException {
        URL url = new URL(host + "api/files/" + fileid + "/metadata?key=" + key);

        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setRequestProperty("Content-Type", "application/json");
        conn.setDoOutput(true);

        DataOutputStream wr = new DataOutputStream(conn.getOutputStream());
        mapper.writeValue(wr, metadata);
        wr.flush();
        wr.close();

        int responseCode = conn.getResponseCode();
        if (responseCode != 200) {
            throw (new IOException("Error uploading metadata [code=" + responseCode + "]"));
        }

        BufferedReader in = new BufferedReader(new InputStreamReader(conn.getInputStream()));
        String inputLine;
        StringBuffer response = new StringBuffer();

        while ((inputLine = in.readLine()) != null) {
            response.append(inputLine);
        }
        in.close();

        return response.toString();
    }
}