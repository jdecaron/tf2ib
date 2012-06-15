<?
Class Connection {
    var $connection;
    var $database = "tf2c";
    var $password = "password";
    var $server = "mysql.tf2scrim.org";
    var $username= "tf2pug";

    function connect(){
        $this->connection = mysql_connect($this->server, $this->username, $this->password);
    }
    
    function close(){
        mysql_close();  
    }
}

Class Database extends Connection{
    // Escape dangerous strings to prevent
    // any MySQL injections.
    function sqlEscapeString($data){
        
        // Process a whole array.
        if(is_array($data)) {
            if(get_magic_quotes_gpc()) {
                $data = array_map("stripslashes", $data);
            }
            $data = array_map("mysql_real_escape_string", $data);
        }
        // Process a single variable.
        else {
            if(get_magic_quotes_gpc()) {
                $data = stripslashes($data);
            }
            $data = mysql_real_escape_string($data);
        }
        
        return $data;
    }

    // Run the query and return the result as a MySQL PHP ressource.
    function query($query){
            $result = mysql_db_query($this->database, $query) or die ("Invalid Query: " . $query);
            return $result;
    }
    
    // Run the query and fetch the result in an array.
    function queryAssoc($query){
            $result = mysql_db_query($this->database, $query) or die ("Invalid Query: " . $query);
    
            if(mysql_num_rows($result) != 0){
                    while($row_array = mysql_fetch_assoc($result)){
                            $data_array[] = $row_array;
                    }
                    return $data_array;
            }
            else{
                    return false;
            }
    }

    function verifyIfRowExists($tableName, $columnName, $rowValue){
        $query = "SELECT * FROM {$tableName} WHERE $columnName = \"{$rowValue}\"";
        $this->connect();   
        mysql_db_query($this->database, $query) or die ("Invalid query:".$query);
        
        if (mysql_affected_rows()){
            return true;
        }
        else{
            return false;
        }
    }
    
    function __construct(){
        // Connect to the database.
            $this->connect();
    }

    function __destruct(){
        // Disconnect to the database.
        $this->close();
    }
}
?>

