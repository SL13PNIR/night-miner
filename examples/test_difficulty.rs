use night_miner::miner::difficulty_to_level;

fn main() {
    println!("00007FFF: {}", difficulty_to_level("00007FFF"));
    println!("0000FFFF: {}", difficulty_to_level("0000FFFF"));
    println!("0001FFFF: {}", difficulty_to_level("0001FFFF"));
    println!("000FFFFF: {}", difficulty_to_level("000FFFFF"));
    println!("00FFFFFF: {}", difficulty_to_level("00FFFFFF"));
}
