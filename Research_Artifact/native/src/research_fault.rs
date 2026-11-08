//! Inactive research instrumentation, shared by every method.
pub fn checkpoint(name: &str) {
    if name=="after_native" {
        if let Ok(path)=std::env::var("RECEIPTCOORDINATOR_RESEARCH_CORRUPT") {
            let _=std::fs::write(path,b"EXTERNAL CHANGE BEFORE OUTCOME VALIDATION\n");
        }
    }
    if std::env::var("RECEIPTCOORDINATOR_RESEARCH_FAULT").ok().as_deref()==Some(name) {std::process::exit(86);}
}
pub fn trace(tool:&str,command:&str) {
    use std::io::Write;
    if let Ok(path)=std::env::var("RECEIPTCOORDINATOR_RESEARCH_TRACE") {
        if let Ok(mut file)=std::fs::OpenOptions::new().create(true).append(true).open(path) {
            let _=writeln!(file,"{}",serde_json::json!({"tool":tool,"command":command}));let _=file.flush();
        }
    }
}
pub fn profile(tool:&str,command:&str,elapsed:u128) {
    use std::io::Write;
    if let Ok(path)=std::env::var("RECEIPTCOORDINATOR_RESEARCH_PROFILE") {
        if let Ok(mut file)=std::fs::OpenOptions::new().create(true).append(true).open(path) {
            let _=writeln!(file,"{}",serde_json::json!({"tool":tool,"command":command,"elapsed_ns":elapsed}));let _=file.flush();
        }
    }
}

pub struct Span {name:&'static str,start:std::time::Instant}
impl Span {pub fn new(name:&'static str)->Self {Self{name,start:std::time::Instant::now()}}}
impl Drop for Span {fn drop(&mut self){
 use std::io::Write;
 if let Ok(path)=std::env::var("RECEIPTCOORDINATOR_COMPONENT_PROFILE") {
  if let Ok(mut f)=std::fs::OpenOptions::new().create(true).append(true).open(path) {
   let _=writeln!(f,"{}",serde_json::json!({"component":self.name,"elapsed_ns":self.start.elapsed().as_nanos()}));
  }
 }
}}
